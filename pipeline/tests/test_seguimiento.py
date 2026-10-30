"""Conexion SQLite local sin ejecuciones ni duplicacion del experimento."""

import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from config import ARCHIVO_BASE_MLFLOW, CARPETA_ARTEFACTOS_MLFLOW, cargar_configuracion
from seguimiento import conectar, registrar_ejecucion


class PruebasSeguimiento(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory(prefix="lab11 seguimiento ")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name).resolve()
        self.ruta_config = self.raiz / "configuracion.toml"
        self.ruta_config.write_bytes((RAIZ / "configuracion.toml").read_bytes())
        self.config = cargar_configuracion(self.ruta_config)

    def conectar(self):
        with redirect_stdout(StringIO()):
            return conectar(self.config)

    def test_crea_sqlite_reutiliza_experimento_y_no_crea_ejecuciones(self):
        cliente, primero = self.conectar()
        _, segundo = self.conectar()
        self.assertEqual(primero.experiment_id, segundo.experiment_id)
        self.assertTrue((self.config["rutas"]["mlflow"] / ARCHIVO_BASE_MLFLOW).is_file())
        self.assertEqual(primero.artifact_location, (self.config["rutas"]["mlflow"] / CARPETA_ARTEFACTOS_MLFLOW).as_uri())
        self.assertEqual(len(cliente.search_runs([primero.experiment_id])), 0)
        self.assertEqual(len([e for e in cliente.search_experiments() if e.name == primero.name]), 1)
        self.assertFalse(self.config["rutas"]["publicaciones"].exists())

    def test_ignora_uri_remota_del_entorno_y_directorio_de_trabajo(self):
        actual = Path.cwd()
        try:
            os.chdir(self.raiz)
            with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "http://127.0.0.1:9", "MLFLOW_REGISTRY_URI": "http://127.0.0.1:9"}):
                cliente, experimento = self.conectar()
            self.assertEqual(cliente.get_experiment(experimento.experiment_id).name, self.config["seguimiento"]["experimento"])
            self.assertFalse((self.raiz / "mlflow.db").exists())
        finally:
            os.chdir(actual)

    def test_experimento_eliminado_no_se_restaura_sin_pedirlo(self):
        cliente, experimento = self.conectar()
        cliente.delete_experiment(experimento.experiment_id)
        with self.assertRaisesRegex(ValueError, "activo"):
            self.conectar()

    def test_ubicacion_de_artefactos_diferente_se_rechaza(self):
        from mlflow import MlflowClient
        carpeta = self.config["rutas"]["mlflow"]
        carpeta.mkdir(parents=True)
        cliente = MlflowClient(tracking_uri=f"sqlite:///{(carpeta / ARCHIVO_BASE_MLFLOW).as_posix()}")
        cliente.create_experiment(self.config["seguimiento"]["experimento"], artifact_location=(self.raiz / "otra").as_uri())
        with self.assertRaisesRegex(ValueError, "carpeta local configurada"):
            self.conectar()

    def test_inicio_y_cierre_sin_metricas_inventadas(self):
        with redirect_stdout(StringIO()), registrar_ejecucion(self.config) as registro:
            registro.iniciar_etapa("01_ingesta.py")
            registro.completar_etapa("01_ingesta.py")
        run = registro.cliente.get_run(registro.id_ejecucion)
        self.assertEqual(run.info.status, "FINISHED")
        self.assertIsNotNone(run.info.end_time)
        self.assertGreaterEqual(run.info.end_time, run.info.start_time)
        self.assertEqual(run.data.tags["etapa.01_ingesta.py.estado"], "completada")
        self.assertEqual(run.data.tags["publicacion"], "no_evaluada")
        self.assertEqual(run.data.metrics, {})

    def test_fallo_registra_causa_y_etapa_sin_declarar_completada(self):
        with redirect_stdout(StringIO()), self.assertRaisesRegex(ValueError, "fecha invalida"):
            with registrar_ejecucion(self.config) as registro:
                registro.iniciar_etapa("01_ingesta.py")
                registro.completar_etapa("01_ingesta.py")
                registro.iniciar_etapa("02_validacion.py")
                raise ValueError("fecha invalida")
        run = registro.cliente.get_run(registro.id_ejecucion)
        self.assertEqual(run.info.status, "FAILED")
        self.assertEqual(run.data.tags["error_causa"], "fecha invalida")
        self.assertEqual(run.data.tags["etapa.02_validacion.py.estado"], "fallida")
        self.assertEqual(run.data.tags["etapas_completadas"], '["01_ingesta.py"]')
        self.assertEqual(run.data.metrics, {})

    def test_interrupcion_se_identifica_como_killed(self):
        with redirect_stdout(StringIO()), self.assertRaises(KeyboardInterrupt):
            with registrar_ejecucion(self.config) as registro:
                registro.iniciar_etapa("01_ingesta.py")
                raise KeyboardInterrupt("interrupcion de prueba")
        run = registro.cliente.get_run(registro.id_ejecucion)
        self.assertEqual(run.info.status, "KILLED")
        self.assertEqual(run.data.tags["etapa.01_ingesta.py.estado"], "interrumpida")
