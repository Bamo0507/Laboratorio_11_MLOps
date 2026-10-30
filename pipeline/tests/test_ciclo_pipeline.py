"""Seguimiento del orquestador real con datos sinteticos y un fallo controlado."""

import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO

import test_ajuste as apoyo
from test_ajuste import RAIZ
from seguimiento import conectar


class PruebasCicloPipeline(unittest.TestCase):
    setUp = apoyo.PruebasAjuste.setUp
    guardar_fuentes = apoyo.PruebasAjuste.guardar_fuentes
    etapas_previas = apoyo.PruebasAjuste.etapas_previas

    def ejecutar_comando(self):
        return subprocess.run(
            [sys.executable, str(RAIZ / "src" / "run_pipeline.py"), "--config", str(self.ruta_config)],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "MLFLOW_DISABLE_AGENT_HINT": "1"},
            check=False,
        )

    def test_corrida_completa_y_fallo_posterior_tienen_registros_independientes(self):
        correcto = self.ejecutar_comando()
        self.assertEqual(correcto.returncode, 0, correcto.stdout + correcto.stderr)
        with redirect_stdout(StringIO()):
            cliente, experimento = conectar(self.config)
        primero = cliente.search_runs([experimento.experiment_id])[0]
        self.assertEqual(primero.info.status, "FINISHED")
        self.assertEqual(primero.data.tags["etapa.07_publicacion.py.estado"], "completada")
        self.assertIn(primero.data.tags["publicacion"], ("publicado", "no_publicado"))
        self.assertEqual(set(primero.data.metrics), {"sarima.mae", "sarima.rmse", "referencia.mae", "referencia.rmse"})
        self.assertIn("mlflow.source.git.commit", primero.data.tags)
        self.assertIn("fuente.entrenamiento.sha256", primero.data.params)
        self.assertIn("modelo.orden", primero.data.params)
        self.assertEqual(primero.data.tags["control.columnas_tipos"], "ok")
        self.assertTrue(cliente.list_artifacts(primero.info.run_id, "modelo"))
        self.conjuntos["entrenamiento"] = self.conjuntos["entrenamiento"].drop(columns=[self.config["columnas"]["valor"]])
        self.guardar_fuentes()
        fallido = self.ejecutar_comando()
        self.assertNotEqual(fallido.returncode, 0)
        runs = cliente.search_runs([experimento.experiment_id], order_by=["attributes.start_time DESC"])
        self.assertEqual(len(runs), 2)
        segundo = runs[0]
        self.assertNotEqual(primero.info.run_id, segundo.info.run_id)
        self.assertEqual(segundo.info.status, "FAILED")
        self.assertEqual(segundo.data.tags["etapa_actual"], "01_ingesta.py")
        self.assertEqual(segundo.data.tags["etapas_completadas"], "[]")
        self.assertIn(self.config["columnas"]["valor"], segundo.data.tags["error_causa"])
        self.assertEqual(segundo.data.tags["publicacion"], "no_evaluada")
        self.assertEqual(segundo.data.metrics, {})
