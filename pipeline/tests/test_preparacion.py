"""Preparacion sin residentes, sin fuga temporal y con validacion vigente."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
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
preparacion = cargar_etapa("03_preparacion")


class PruebasPreparacion(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory(prefix="lab11_preparacion_")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name) / "pipeline"
        self.raiz.mkdir()
        self.ruta_config = self.raiz / "configuracion.toml"
        self.ruta_config.write_bytes((RAIZ / "configuracion.toml").read_bytes())
        self.config = cargar_configuracion(self.ruta_config)
        self.col = self.config["columnas"]
        fechas = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-03-01"), *pd.date_range("2023-01-01", "2026-06-01", freq="MS")]
        filas = [self.fila(fecha) for fecha in fechas]
        filas += [self.fila(pd.Timestamp("2020-01-01"), pais="Guatemala", valor="500"),
                  self.fila(pd.Timestamp("2020-02-01"), pais="Guatemala", valor="900")]
        self.conjuntos = {
            "entrenamiento": pd.DataFrame([f for f in filas if f[self.col["fecha"]] < "2026-01-01"]),
            "prueba": pd.DataFrame([f for f in filas if f[self.col["fecha"]] >= "2026-01-01"]),
        }
        self.guardar_fuentes()

    def fila(self, fecha: pd.Timestamp, pais: str = "El Salvador", valor: str = "100.25") -> dict[str, str]:
        fila = {columna: "categoria" for columna in columnas_requeridas(self.config)}
        fila.update({self.col["fecha"]: fecha.strftime("%Y-%m-%d"), self.col["anio"]: str(fecha.year),
                     self.col["mes"]: str(fecha.month), self.col["pais"]: pais,
                     self.col["tipo"]: "Turista", self.col["valor"]: valor})
        return fila

    def guardar_fuentes(self) -> None:
        for clave, datos in self.conjuntos.items():
            self.config["rutas"][clave].parent.mkdir(parents=True, exist_ok=True)
            datos.to_csv(self.config["rutas"][clave], index=False)

    def etapas_previas(self) -> None:
        with redirect_stdout(StringIO()):
            ingesta.ejecutar(self.ruta_config)
            validacion.ejecutar(self.ruta_config)

    def ejecutar(self) -> dict:
        self.etapas_previas()
        with redirect_stdout(StringIO()):
            return preparacion.ejecutar(self.ruta_config)

    @staticmethod
    def huella(ruta: Path) -> str:
        return hashlib.sha256(ruta.read_bytes()).hexdigest()

    def comprobar_rechazo_sin_reemplazo(self, motivo: str) -> None:
        anteriores = {clave: self.huella(self.config["rutas"][clave]) for clave in ("serie_mensual", "ajuste", "evaluacion")}
        with redirect_stdout(StringIO()), self.assertRaisesRegex(ValueError, motivo):
            preparacion.ejecutar(self.ruta_config)
        reporte = json.loads(self.config["rutas"]["reporte_preparacion"].read_text())
        self.assertEqual(reporte["estado"], "rechazado")
        for clave, sha in anteriores.items():
            self.assertEqual(self.huella(self.config["rutas"][clave]), sha)

    def test_excluye_residentes_y_deja_huecos_sin_inventar_ceros(self) -> None:
        reporte = self.ejecutar()
        serie = pd.read_csv(self.config["rutas"]["serie_mensual"])
        enero = serie.loc[serie.fecha.eq("2020-01-01")].iloc[0]
        febrero = serie.loc[serie.fecha.eq("2020-02-01")].iloc[0]
        self.assertEqual(enero.viajeros, 100.25)
        self.assertTrue(pd.isna(febrero.viajeros))
        self.assertEqual(febrero.registros, 0)
        self.assertEqual(reporte["filas_residentes_excluidas"], 2)
        self.assertEqual(reporte["meses_ajuste"], 36)
        self.assertEqual(reporte["meses_evaluacion"], 6)
        self.assertFalse(reporte["publicacion_autorizada"])

    def test_cambiar_observaciones_de_evaluacion_no_cambia_el_ajuste(self) -> None:
        self.ejecutar()
        anterior = self.huella(self.config["rutas"]["ajuste"])
        self.conjuntos["prueba"][self.col["valor"]] = "999999.75"
        self.guardar_fuentes()
        self.ejecutar()
        self.assertEqual(self.huella(self.config["rutas"]["ajuste"]), anterior)

    def test_no_descarta_coincidencias_parciales_validas_al_sumar(self) -> None:
        extra = self.conjuntos["prueba"].iloc[:1].copy()
        extra["Agrupación Residencia"] = "otra agrupacion"
        extra[self.col["valor"]] = "25.125"
        self.conjuntos["prueba"] = pd.concat([self.conjuntos["prueba"], extra], ignore_index=True)
        self.guardar_fuentes()
        self.ejecutar()
        evaluacion = pd.read_csv(self.config["rutas"]["evaluacion"])
        self.assertEqual(evaluacion.iloc[0].viajeros, 125.375)
        self.assertEqual(evaluacion.iloc[0].registros, 2)

    def test_rechaza_un_reporte_de_calidad_no_apto(self) -> None:
        self.ejecutar()
        ruta = self.config["rutas"]["reporte_validacion"]
        reporte = json.loads(ruta.read_text())
        reporte["apto_para_preparacion"] = False
        ruta.write_text(json.dumps(reporte))
        self.comprobar_rechazo_sin_reemplazo("el reporte de calidad permite")

    def test_rechaza_csv_validado_modificado(self) -> None:
        self.ejecutar()
        with self.config["rutas"]["validado"].open("a") as archivo:
            archivo.write("\n")
        self.comprobar_rechazo_sin_reemplazo("el CSV validado coincide")

    def test_rechaza_fuente_modificada_despues_de_validar(self) -> None:
        self.ejecutar()
        with self.config["rutas"]["prueba"].open("a") as archivo:
            archivo.write("\n")
        self.comprobar_rechazo_sin_reemplazo("la fuente original no cambio")

    def test_cambiar_configuracion_exige_validar_de_nuevo(self) -> None:
        self.ejecutar()
        self.ruta_config.write_text(self.ruta_config.read_text().replace('inicio_ajuste = "2023-01"', 'inicio_ajuste = "2023-02"'))
        self.comprobar_rechazo_sin_reemplazo("la configuracion coincide")
        reporte = self.ejecutar()
        self.assertEqual(reporte["meses_ajuste"], 35)

    def test_repetibilidad_y_portabilidad_de_la_preparacion(self) -> None:
        reporte = self.ejecutar()
        anteriores = {clave: self.huella(self.config["rutas"][clave]) for clave in ("serie_mensual", "ajuste", "evaluacion")}
        self.ejecutar()
        for clave, sha in anteriores.items():
            self.assertEqual(self.huella(self.config["rutas"][clave]), sha)
        copia = self.raiz.parent / "Otra ubicacion con espacios y acentos á"
        shutil.copytree(self.raiz, copia)
        proceso = subprocess.run(
            [sys.executable, str(RAIZ / "src/03_preparacion.py"), "--config", str(copia / "configuracion.toml")],
            cwd=copia.parent, capture_output=True, text=True, check=False,
        )
        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        nueva = cargar_configuracion(copia / "configuracion.toml")
        for clave, sha in anteriores.items():
            self.assertEqual(self.huella(nueva["rutas"][clave]), sha)
        self.assertEqual(reporte["estado"], "completada")
