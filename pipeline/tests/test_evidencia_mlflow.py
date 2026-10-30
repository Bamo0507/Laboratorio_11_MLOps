"""Evidencia completa consultada desde MLflow y comparacion sensible a cambios."""

import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import test_ajuste as apoyo
from evidencia_mlflow import comparar, verificar
from seguimiento import conectar
from utils import cargar_json


class PruebasEvidenciaMlflow(unittest.TestCase):
    setUp = apoyo.PruebasAjuste.setUp
    guardar_fuentes = apoyo.PruebasAjuste.guardar_fuentes
    etapas_previas = apoyo.PruebasAjuste.etapas_previas

    def test_dos_runs_completos_fallo_con_copia_y_comparacion_detecta_cambios(self):
        with redirect_stdout(StringIO()):
            evidencia = verificar(self.ruta_config)
            cliente, experimento = conectar(self.config)
        self.assertTrue(evidencia["comparacion"]["equivalentes"])
        self.assertEqual(evidencia["comparacion"]["diferencia_maxima_metricas"], 0)
        self.assertEqual(len(evidencia["consulta"]), 3)
        for run in evidencia["consulta"][:2]:
            self.assertEqual(run["estado"], "FINISHED")
            self.assertEqual(len(run["metricas"]), 4)
            self.assertIn("modelo/04_modelo_sarima.pkl", run["artefactos"])
            self.assertIn("configuracion/configuracion.toml", run["artefactos"])
            self.assertIn("codigo/version.json", run["artefactos"])
            carpeta = self.raiz / "descargas" / run["id_ejecucion"]
            carpeta.mkdir(parents=True)
            reporte = cliente.download_artifacts(run["id_ejecucion"], "reportes/06_exportacion.json", str(carpeta))
            self.assertEqual(cargar_json(Path(reporte))["id_ejecucion_mlflow"], run["id_ejecucion"])
        fallido = evidencia["consulta"][2]
        self.assertEqual(fallido["estado"], "FAILED")
        self.assertFalse(fallido["metricas"])
        self.assertIn("ejecucion/error.json", fallido["artefactos"])
        self.assertTrue(evidencia["fallo_controlado"]["originales_intactos"])
        self.assertTrue(evidencia["fallo_controlado"]["vigente_conservado"])
        primero, segundo = evidencia["comparacion"]["runs"]
        cliente.log_metric(segundo, "sarima.mae", 999999)
        with redirect_stdout(StringIO()), self.assertRaisesRegex(ValueError, "metricas equivalentes"):
            comparar(cliente, primero, segundo, 1e-12, 1e-8)
