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
        with redirect_stdout(StringIO()):
            con_cero = evaluacion.metricas(np.array([0, 10]), np.array([1, 11]))
        self.assertEqual(con_cero, {"mae": 1., "rmse": 1.})

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

    def test_valores_reservados_cambiados_no_alteran_pronosticos(self):
        primero = self.evaluar()
        inicial = pd.read_csv(self.config["rutas"]["comparacion"])
        self.conjuntos["prueba"][self.config["columnas"]["valor"]] = "999999.75"
        self.guardar_fuentes()
        self.etapas_previas()
        segundo = self.evaluar()
        cambiado = pd.read_csv(self.config["rutas"]["comparacion"])
        np.testing.assert_allclose(inicial["sarima"], cambiado["sarima"], rtol=1e-12, atol=1e-8)
        np.testing.assert_allclose(inicial["referencia"], cambiado["referencia"], rtol=1e-12, atol=1e-8)
        self.assertNotEqual(primero["metricas"], segundo["metricas"])
        self.assertTrue(cambiado["observado"].eq(999999.75).all())

    def test_protocolo_identifica_corte_meses_ocultos_y_limites_historicos(self):
        reporte = self.evaluar()
        protocolo = reporte["protocolo_temporal"]
        self.assertEqual(protocolo["corte_modelo"], "2025-12")
        self.assertEqual(protocolo["observaciones_ajuste"], 36)
        self.assertEqual(protocolo["horizontes_meses"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(protocolo["meses_ocultos_al_ajuste"][:2], ["2026-01", "2026-02"])
        self.assertEqual(protocolo["meses_referencia"][:2], ["2025-01", "2025-02"])
        self.assertFalse(protocolo["valores_evaluacion_en_ajuste"])
        self.assertFalse(reporte["comparabilidad"]["reproduce_disponibilidad_historica"])

    def test_sin_observaciones_comparables_no_calcula_errores_ni_reemplaza_csv(self):
        self.evaluar()
        previo = huella_archivo(self.config["rutas"]["comparacion"])
        self.ruta_config.write_text(self.ruta_config.read_text().replace("observaciones_comparables = true", "observaciones_comparables = false"))
        self.etapas_previas()
        with redirect_stdout(StringIO()):
            ajuste.ejecutar(self.ruta_config)
        with self.assertRaisesRegex(ValueError, "sin ellas no se calculan errores"), redirect_stdout(StringIO()):
            evaluacion.ejecutar(self.ruta_config)
        from utils import cargar_json
        reporte = cargar_json(self.config["rutas"]["reporte_evaluacion"])
        self.assertEqual(reporte["estado"], "rechazado")
        self.assertNotIn("metricas", reporte)
        self.assertEqual(previo, huella_archivo(self.config["rutas"]["comparacion"]))

    def test_diagnostico_no_divide_por_error_cero_de_referencia(self):
        reales = np.array([10., 20.])
        predichos = np.array([13., 22.])
        with redirect_stdout(StringIO()):
            resultados = {"sarima": evaluacion.metricas(reales, predichos), "referencia": evaluacion.metricas(reales, reales)}
        diagnostico = evaluacion.diagnosticar(reales, predichos, reales, resultados)
        self.assertEqual(diagnostico["aumento_relativo_error_frente_referencia"], {"mae": None, "rmse": None})
        self.assertEqual(diagnostico["meses_sobreestimados_sarima"], 2)
        self.assertEqual(diagnostico["meses_con_menor_error_referencia"], 2)
