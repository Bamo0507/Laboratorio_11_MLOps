"""Fallos controlados de los seis controles usando copias sinteticas temporales."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from config import cargar_configuracion, columnas_requeridas  # noqa: E402


def cargar_etapa(nombre: str):
    spec = importlib.util.spec_from_file_location(nombre, RAIZ / "src" / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


ingesta = cargar_etapa("01_ingesta")
validacion = cargar_etapa("02_validacion")


class PruebasValidacion(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory(prefix="lab11_calidad_")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.ruta_config = self.raiz / "configuracion.toml"
        self.ruta_config.write_bytes((RAIZ / "configuracion.toml").read_bytes())
        self.config = cargar_configuracion(self.ruta_config)
        col = self.config["columnas"]
        filas = []
        for fecha in pd.date_range("2023-01-01", "2026-06-01", freq="MS"):
            fila = {nombre: "categoria" for nombre in columnas_requeridas(self.config)}
            fila.update({col["fecha"]: fecha.strftime("%Y-%m-%d"), col["anio"]: str(fecha.year),
                         col["mes"]: str(fecha.month), col["pais"]: "El Salvador",
                         col["tipo"]: "Turista", col["valor"]: "100"})
            filas.append(fila)
        self.conjuntos = {"entrenamiento": pd.DataFrame(filas[:-6]), "prueba": pd.DataFrame(filas[-6:])}
        self.guardar_fuentes()
        self.publicado = self.config["rutas"]["publicaciones"] / "anterior" / "estimaciones.json"
        self.publicado.parent.mkdir(parents=True)
        self.publicado.write_text('{"version": "anterior"}\n')
        self.hash_publicado = self.huella(self.publicado)

    @staticmethod
    def huella(ruta: Path) -> str:
        return hashlib.sha256(ruta.read_bytes()).hexdigest()

    def guardar_fuentes(self) -> None:
        for clave, datos in self.conjuntos.items():
            ruta = self.config["rutas"][clave]
            ruta.parent.mkdir(parents=True, exist_ok=True)
            datos.to_csv(ruta, index=False)

    def ejecutar(self) -> dict:
        with redirect_stdout(StringIO()):
            ingesta.ejecutar(self.ruta_config)
            return validacion.ejecutar(self.ruta_config)

    def comprobar_fallo(self, codigo: str) -> dict:
        with self.assertRaises(ValueError):
            self.ejecutar()
        resultado = json.loads(self.config["rutas"]["reporte_validacion"].read_text())
        self.assertFalse(resultado["apto_para_preparacion"])
        self.assertFalse(resultado["publicacion_autorizada"])
        self.assertEqual(len(resultado["controles"]), 6)
        self.assertEqual(next(c for c in resultado["controles"] if c["codigo"] == codigo)["estado"], "error")
        self.assertEqual(self.huella(self.publicado), self.hash_publicado)
        return resultado

    def test_fuente_valida_cubre_ajuste_prueba_y_referencia(self) -> None:
        originales = {clave: self.huella(self.config["rutas"][clave]) for clave in self.conjuntos}
        resultado = self.ejecutar()
        self.assertTrue(resultado["apto_para_preparacion"])
        self.assertTrue(all(c["estado"] == "ok" for c in resultado["controles"]))
        self.assertEqual(resultado["filas_entrada"], 42)
        for clave, sha in originales.items():
            self.assertEqual(self.huella(self.config["rutas"][clave]), sha)

    def test_tipo_numerico_incompatible(self) -> None:
        self.conjuntos["prueba"].loc[0, self.config["columnas"]["valor"]] = "sin_numero"
        self.guardar_fuentes()
        self.comprobar_fallo("columnas_tipos")

    def test_fecha_invalida(self) -> None:
        self.conjuntos["prueba"].loc[0, self.config["columnas"]["fecha"]] = "2026-02-30"
        self.guardar_fuentes()
        self.comprobar_fallo("fechas_cobertura")

    def test_mes_ausente_no_se_completa_con_cero_y_conserva_validado(self) -> None:
        self.ejecutar()
        anterior = self.huella(self.config["rutas"]["validado"])
        self.conjuntos["prueba"] = self.conjuntos["prueba"].iloc[1:]
        self.guardar_fuentes()
        resultado = self.comprobar_fallo("fechas_cobertura")
        self.assertEqual(self.huella(self.config["rutas"]["validado"]), anterior)
        control = next(c for c in resultado["controles"] if c["codigo"] == "fechas_cobertura")
        self.assertIn("2026-01", control["detalles"]["meses_sin_cobertura"]["evaluacion"])

    def test_duplicado_completo_se_detecta_entre_archivos(self) -> None:
        self.conjuntos["prueba"] = pd.concat([self.conjuntos["prueba"], self.conjuntos["entrenamiento"].iloc[:1]], ignore_index=True)
        self.guardar_fuentes()
        self.comprobar_fallo("unicidad")

    def test_coincidencia_parcial_no_borra_registros(self) -> None:
        extra = self.conjuntos["prueba"].iloc[:1].copy()
        extra["Agrupación Residencia"] = "otra agrupacion"
        self.conjuntos["prueba"] = pd.concat([self.conjuntos["prueba"], extra], ignore_index=True)
        self.guardar_fuentes()
        resultado = self.ejecutar()
        self.assertTrue(resultado["apto_para_preparacion"])
        control = next(c for c in resultado["controles"] if c["codigo"] == "unicidad")
        self.assertEqual(control["estado"], "advertencia")
        self.assertEqual(len(pd.read_csv(self.config["rutas"]["validado"])), 43)

    def test_faltante_critico(self) -> None:
        self.conjuntos["prueba"].loc[0, self.config["columnas"]["valor"]] = "NaN"
        self.guardar_fuentes()
        self.comprobar_fallo("faltantes")

    def test_faltante_opcional_se_advierte_y_se_conserva(self) -> None:
        for datos in self.conjuntos.values():
            datos["Región"] = ""
        self.guardar_fuentes()
        resultado = self.ejecutar()
        control = next(c for c in resultado["controles"] if c["codigo"] == "faltantes")
        self.assertEqual(control["estado"], "advertencia")
        self.assertTrue(resultado["apto_para_preparacion"])

    def test_negativo_no_finito_y_total_mensual_cero(self) -> None:
        for valor in ("-1", "inf", "0"):
            with self.subTest(valor=valor):
                self.conjuntos["prueba"].loc[0, self.config["columnas"]["valor"]] = valor
                self.guardar_fuentes()
                self.comprobar_fallo("valores_denominadores")

    def test_cero_en_registro_permitido_si_el_total_mensual_es_positivo(self) -> None:
        extra = self.conjuntos["prueba"].iloc[:1].copy()
        extra[self.config["columnas"]["valor"]] = "0"
        extra["Agrupación Residencia"] = "otra agrupacion"
        self.conjuntos["prueba"] = pd.concat([self.conjuntos["prueba"], extra], ignore_index=True)
        self.guardar_fuentes()
        resultado = self.ejecutar()
        control = next(c for c in resultado["controles"] if c["codigo"] == "valores_denominadores")
        self.assertEqual(control["estado"], "ok")

    def test_tipo_ajeno_y_exclusion_de_residentes_son_reglas_criticas(self) -> None:
        self.conjuntos["prueba"].loc[0, self.config["columnas"]["tipo"]] = "Viajero"
        self.guardar_fuentes()
        self.comprobar_fallo("regla_metodologica")
        self.conjuntos["prueba"].loc[0, self.config["columnas"]["tipo"]] = "Turista"
        self.guardar_fuentes()
        self.ruta_config.write_text(self.ruta_config.read_text().replace('paises_excluidos = ["Guatemala"]', 'paises_excluidos = ["Otro pais"]'))
        self.comprobar_fallo("regla_metodologica")

    def test_fuente_modificada_despues_de_ingesta(self) -> None:
        with redirect_stdout(StringIO()):
            ingesta.ejecutar(self.ruta_config)
        with self.config["rutas"]["prueba"].open("a") as archivo:
            archivo.write("\n")
        with redirect_stdout(StringIO()), self.assertRaises(ValueError):
            validacion.ejecutar(self.ruta_config)
        resultado = json.loads(self.config["rutas"]["reporte_validacion"].read_text())
        control = next(c for c in resultado["controles"] if c["codigo"] == "regla_metodologica")
        self.assertEqual(control["estado"], "error")

    def test_columna_ausente_desde_fuente_genera_reporte_y_detiene_orquestador(self) -> None:
        self.conjuntos["prueba"] = self.conjuntos["prueba"].drop(columns=[self.config["columnas"]["pais"]])
        self.guardar_fuentes()
        resultado = subprocess.run(
            [sys.executable, str(RAIZ / "src/run_pipeline.py"), "--config", str(self.ruta_config)],
            cwd=self.raiz, capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(resultado.returncode, 0)
        reporte = json.loads(self.config["rutas"]["reporte_validacion"].read_text())
        self.assertEqual(reporte["controles"][0]["estado"], "error")
        self.assertTrue(all(c["estado"] == "no_evaluado" for c in reporte["controles"][1:]))
        self.assertEqual(self.huella(self.publicado), self.hash_publicado)
