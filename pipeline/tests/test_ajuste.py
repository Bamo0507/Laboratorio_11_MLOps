"""Ajuste con entrenamiento aislado, persistencia y fallos controlados."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAXResults

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
ajuste = cargar_etapa("04_ajuste")


class PruebasAjuste(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory(prefix="lab11_ajuste_")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.ruta_config = self.raiz / "configuracion.toml"
        self.ruta_config.write_bytes((RAIZ / "configuracion.toml").read_bytes())
        self.config = cargar_configuracion(self.ruta_config)
        col = self.config["columnas"]
        t = np.arange(42)
        valores = 100 + 0.5 * t + 10 * np.sin(2 * np.pi * t / 12) + np.random.default_rng(5).normal(0, 15, 42)
        filas = []
        for fecha, valor in zip(pd.date_range("2023-01-01", "2026-06-01", freq="MS"), valores):
            fila = {nombre: "categoria" for nombre in columnas_requeridas(self.config)}
            fila.update({col["fecha"]: fecha.strftime("%Y-%m-%d"), col["anio"]: str(fecha.year),
                         col["mes"]: str(fecha.month), col["pais"]: "El Salvador",
                         col["tipo"]: "Turista", col["valor"]: str(valor)})
            filas.append(fila)
        self.conjuntos = {"entrenamiento": pd.DataFrame(filas[:36]), "prueba": pd.DataFrame(filas[36:])}
        self.guardar_fuentes()
        self.etapas_previas()

    def guardar_fuentes(self) -> None:
        for clave, datos in self.conjuntos.items():
            self.config["rutas"][clave].parent.mkdir(parents=True, exist_ok=True)
            datos.to_csv(self.config["rutas"][clave], index=False)

    def etapas_previas(self) -> None:
        with redirect_stdout(StringIO()):
            ingesta.ejecutar(self.ruta_config)
            validacion.ejecutar(self.ruta_config)
            preparacion.ejecutar(self.ruta_config)

    def ejecutar(self) -> dict:
        with redirect_stdout(StringIO()):
            return ajuste.ejecutar(self.ruta_config)

    def modelo(self):
        return SARIMAXResults.load(self.config["rutas"]["modelo_ajustado"])

    def huella_modelo(self) -> str:
        return hashlib.sha256(self.config["rutas"]["modelo_ajustado"].read_bytes()).hexdigest()

    def comprobar_rechazo(self, sha_previo: str) -> None:
        self.assertEqual(self.huella_modelo(), sha_previo)
        reporte = json.loads(self.config["rutas"]["reporte_ajuste"].read_text())
        self.assertEqual(reporte["estado"], "rechazado")
        self.assertFalse(reporte["publicacion_autorizada"])
        self.assertNotIn("metricas_evaluacion", reporte)

    def test_modelo_recuperado_contiene_solo_los_36_meses_de_ajuste(self) -> None:
        reporte = self.ejecutar()
        modelo = self.modelo()
        self.assertEqual(modelo.nobs, 36)
        self.assertEqual(modelo.model.data.dates[-1], pd.Timestamp("2025-12-01"))
        self.assertTrue(reporte["convergencia"]["convergio"])
        self.assertFalse(reporte["publicacion_autorizada"])
        self.assertTrue(np.isfinite(modelo.params).all())
        self.assertNotIn("metricas_evaluacion", reporte)

    def test_puede_ajustar_sin_abrir_el_csv_de_evaluacion(self) -> None:
        self.config["rutas"]["evaluacion"].unlink()
        reporte = self.ejecutar()
        self.assertEqual(reporte["estado"], "completada")

    def test_evaluacion_no_influye_en_parametros_aprendidos(self) -> None:
        self.ejecutar()
        parametros = self.modelo().params.copy()
        self.conjuntos["prueba"][self.config["columnas"]["valor"]] = "999999.75"
        self.guardar_fuentes()
        self.etapas_previas()
        self.ejecutar()
        np.testing.assert_allclose(self.modelo().params, parametros, rtol=1e-12, atol=1e-12)

    def test_repetir_el_ajuste_conserva_parametros_y_predicciones(self) -> None:
        self.ejecutar()
        primero = self.modelo()
        parametros, prediccion = primero.params.copy(), primero.forecast(6)
        self.ejecutar()
        segundo = self.modelo()
        np.testing.assert_allclose(segundo.params, parametros, rtol=1e-12, atol=1e-12)
        np.testing.assert_allclose(segundo.forecast(6), prediccion, rtol=1e-12, atol=1e-12)

    def test_no_convergencia_conserva_modelo_anterior(self) -> None:
        self.ejecutar()
        anterior = self.huella_modelo()
        with patch.object(ajuste, "SARIMAX") as constructor:
            constructor.return_value.fit.return_value = SimpleNamespace(mle_retvals={"converged": False})
            with self.assertRaisesRegex(ValueError, "convergencia"):
                self.ejecutar()
        self.comprobar_rechazo(anterior)

    def test_fallo_al_recuperar_el_binario_conserva_modelo_anterior(self) -> None:
        self.ejecutar()
        anterior = self.huella_modelo()
        with patch.object(ajuste.SARIMAXResults, "load", side_effect=ValueError("Fallo de recuperacion simulado")):
            with self.assertRaisesRegex(ValueError, "Fallo de recuperacion"):
                self.ejecutar()
        self.comprobar_rechazo(anterior)
        self.assertFalse(list(self.config["rutas"]["procesados"].glob("*.tmp")))

    def test_configuracion_modificada_y_archivo_alterado_impiden_ajustar(self) -> None:
        self.ejecutar()
        anterior = self.huella_modelo()
        original = self.ruta_config.read_text()
        self.ruta_config.write_text(original.replace("iteraciones_maximas = 200", "iteraciones_maximas = 201"))
        with self.assertRaisesRegex(ValueError, "configuracion no cambio"):
            self.ejecutar()
        self.comprobar_rechazo(anterior)
        self.ruta_config.write_text(original)
        with self.config["rutas"]["ajuste"].open("a") as archivo:
            archivo.write("\n")
        with self.assertRaisesRegex(ValueError, "archivo de ajuste coincide"):
            self.ejecutar()
        self.comprobar_rechazo(anterior)

    def test_reporte_de_preparacion_rechazado_impide_ajustar(self) -> None:
        self.ejecutar()
        anterior = self.huella_modelo()
        ruta = self.config["rutas"]["reporte_preparacion"]
        reporte = json.loads(ruta.read_text())
        reporte["estado"] = "rechazado"
        ruta.write_text(json.dumps(reporte))
        with self.assertRaisesRegex(ValueError, "preparacion termino"):
            self.ejecutar()
        self.comprobar_rechazo(anterior)
