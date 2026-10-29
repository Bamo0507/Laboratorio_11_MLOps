"""Errores fuera de muestra, regla previa y vigencia de artefactos."""

from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np
import pandas as pd

import test_ajuste as apoyo
from test_ajuste import ajuste, cargar_etapa
from utils import huella_archivo

evaluacion = cargar_etapa("05_evaluacion")


class PruebasEvaluacion(unittest.TestCase):
    setUp = apoyo.PruebasAjuste.setUp
    guardar_fuentes = apoyo.PruebasAjuste.guardar_fuentes
    etapas_previas = apoyo.PruebasAjuste.etapas_previas

    def evaluar(self):
        with redirect_stdout(StringIO()):
            ajuste.ejecutar(self.ruta_config)
            return evaluacion.ejecutar(self.ruta_config)

    def test_formulas_con_errores_conocidos(self):
        with redirect_stdout(StringIO()):
            valores = evaluacion.metricas(np.array([10, 20]), np.array([13, 16]))
        self.assertEqual(valores["mae"], 3.5)
        self.assertAlmostEqual(valores["rmse"], np.sqrt(12.5))

    def test_regla_exige_mejorar_ambas_y_rechaza_empate_y_referencia_perfecta(self):
        self.assertTrue(evaluacion.supera_regla({"mae": 1, "rmse": 2}, {"mae": 2, "rmse": 3}))
        for candidato, base in [({"mae": 1, "rmse": 3}, {"mae": 2, "rmse": 3}),
                                ({"mae": 3, "rmse": 2}, {"mae": 2, "rmse": 3}),
                                ({"mae": 0, "rmse": 0}, {"mae": 0, "rmse": 0})]:
            self.assertFalse(evaluacion.supera_regla(candidato, base))

    def test_comparacion_usa_seis_meses_y_exponencial_sin_alterar_modelo(self):
        reporte = self.evaluar()
        rutas = self.config["rutas"]
        anterior = huella_archivo(rutas["modelo_ajustado"])
        modelo = ajuste.SARIMAXResults.load(rutas["modelo_ajustado"])
        tabla = pd.read_csv(rutas["comparacion"])
        serie = pd.read_csv(rutas["serie_mensual"]).set_index("fecha")
        self.assertEqual(len(tabla), 6)
        self.assertEqual(tabla["fecha_referencia"].tolist(), [f"2025-{m:02d}-01" for m in range(1, 7)])
        np.testing.assert_allclose(tabla["referencia"], serie.loc[tabla["fecha_referencia"], "viajeros"])
        np.testing.assert_allclose(tabla["sarima"], np.exp(modelo.forecast(6)))
        for nombre in ("sarima", "referencia"):
            error = tabla[nombre] - tabla["observado"]
            self.assertAlmostEqual(reporte["metricas"][nombre]["mae"], np.abs(error).mean())
            self.assertAlmostEqual(reporte["metricas"][nombre]["rmse"], np.sqrt((error ** 2).mean()))
        self.assertFalse(reporte["publicacion_autorizada"])
        with redirect_stdout(StringIO()):
            segundo = evaluacion.ejecutar(self.ruta_config)
        self.assertEqual(reporte["metricas"], segundo["metricas"])
        self.assertEqual(anterior, huella_archivo(rutas["modelo_ajustado"]))

    def test_archivos_alterados_bloquean_sin_reemplazar_comparacion(self):
        self.evaluar()
        rutas = self.config["rutas"]
        previo = huella_archivo(rutas["comparacion"])
        for nombre in ("modelo_ajustado", "evaluacion", "serie_mensual", "reporte_preparacion"):
            ruta = rutas[nombre]
            contenido = ruta.read_bytes()
            ruta.write_bytes(contenido + b"\n")
            with redirect_stdout(StringIO()), self.assertRaises(ValueError):
                evaluacion.ejecutar(self.ruta_config)
            self.assertEqual(previo, huella_archivo(rutas["comparacion"]))
            ruta.write_bytes(contenido)

    def test_cambiar_regla_despues_del_ajuste_bloquea(self):
        self.evaluar()
        self.ruta_config.write_text(self.ruta_config.read_text() + "\n# cambio posterior\n")
        with redirect_stdout(StringIO()), self.assertRaisesRegex(ValueError, "configuracion no cambio"):
            evaluacion.ejecutar(self.ruta_config)

    def test_metricas_rechazan_no_finitos_y_vectores_distintos(self):
        for real, predicho in [([1], [np.nan]), ([1, 2], [1]), ([], [])]:
            with redirect_stdout(StringIO()), self.assertRaises(ValueError):
                evaluacion.metricas(np.array(real), np.array(predicho))

    def test_desempeno_desfavorable_completa_sin_aprobar(self):
        with redirect_stdout(StringIO()):
            ajuste.ejecutar(self.ruta_config)
        fechas = pd.date_range("2026-01-01", periods=6, freq="MS")
        pronostico = SimpleNamespace(predicted_mean=pd.Series(np.log(np.full(6, 1e9)), index=fechas))
        with redirect_stdout(StringIO()), patch.object(evaluacion.SARIMAXResults, "get_forecast", return_value=pronostico):
            reporte = evaluacion.ejecutar(self.ruta_config)
        self.assertEqual(reporte["estado"], "completada")
        self.assertFalse(reporte["supera_regla_desempeno"])
        self.assertFalse(reporte["publicacion_autorizada"])
