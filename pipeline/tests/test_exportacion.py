"""Exportacion auditable, conservacion de decisiones y bloqueos de insumos."""

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO

import numpy as np

import test_ajuste as apoyo
from test_ajuste import ajuste, cargar_etapa
from utils import cargar_json, huella_archivo

evaluacion = cargar_etapa("05_evaluacion")
exportacion = cargar_etapa("06_exportacion")


class PruebasExportacion(unittest.TestCase):
    setUp = apoyo.PruebasAjuste.setUp
    guardar_fuentes = apoyo.PruebasAjuste.guardar_fuentes
    etapas_previas = apoyo.PruebasAjuste.etapas_previas

    def preparar(self):
        with redirect_stdout(StringIO()):
            ajuste.ejecutar(self.ruta_config)
            evaluacion.ejecutar(self.ruta_config)

    def exportar(self):
        with redirect_stdout(StringIO()):
            return exportacion.ejecutar(self.ruta_config)

    def test_exporta_seis_meses_y_conserva_metricas_sin_tocar_publicaciones(self):
        self.preparar()
        rutas = self.config["rutas"]
        rutas["publicaciones"].mkdir(parents=True)
        vigente = rutas["publicaciones"] / "vigente.json"
        vigente.write_text('{"version": "anterior"}')
        huella_vigente = huella_archivo(vigente)
        resultado = self.exportar()
        candidato = cargar_json(rutas["candidato"])
        reporte = cargar_json(rutas["reporte_evaluacion"])
        self.assertEqual(resultado["estado"], "completada")
        self.assertEqual(len(candidato["estimaciones"]), 6)
        self.assertEqual(candidato["metricas"], reporte["metricas"])
        self.assertEqual(candidato["supera_regla_desempeno"], reporte["supera_regla_desempeno"])
        self.assertEqual(candidato["estimaciones"][0]["fecha"], "2026-01-01")
        self.assertEqual(candidato["estimaciones"][-1]["fecha"], "2026-06-01")
        self.assertFalse(candidato["publicacion_autorizada"])
        self.assertEqual(huella_vigente, huella_archivo(vigente))
        anterior = huella_archivo(rutas["candidato"])
        self.exportar()
        self.assertEqual(anterior, huella_archivo(rutas["candidato"]))
        self.assertEqual(resultado["candidato"]["sha256"], anterior)

    def test_archivos_modificados_rechazan_y_conservan_candidato_anterior(self):
        self.preparar()
        self.exportar()
        rutas = self.config["rutas"]
        previo = huella_archivo(rutas["candidato"])
        for nombre in ("comparacion", "modelo_ajustado", "reporte_ajuste", "reporte_preparacion", "evaluacion", "entrenamiento", "prueba"):
            ruta = rutas[nombre]
            original = ruta.read_bytes()
            ruta.write_bytes(original + b"\n")
            with self.assertRaises(ValueError):
                self.exportar()
            self.assertEqual(previo, huella_archivo(rutas["candidato"]))
            rechazo = cargar_json(rutas["reporte_exportacion"])
            self.assertEqual(rechazo["estado"], "rechazado")
            self.assertFalse(rechazo["publicacion_autorizada"])
            ruta.write_bytes(original)

    def test_reporte_rechazado_decision_incoherente_y_metricas_incorrectas_bloquean(self):
        self.preparar()
        ruta = self.config["rutas"]["reporte_evaluacion"]
        original = ruta.read_bytes()
        for cambio in ("estado", "decision", "metrica", "regla"):
            datos = json.loads(original)
            if cambio == "estado":
                datos["estado"] = "rechazado"
            elif cambio == "decision":
                datos["supera_regla_desempeno"] = not datos["supera_regla_desempeno"]
            elif cambio == "metrica":
                datos["metricas"]["sarima"]["mae"] += 1
            else:
                datos["regla"] = {"regla": "otra"}
            ruta.write_text(json.dumps(datos))
            with self.assertRaises(ValueError):
                self.exportar()
            self.assertFalse(self.config["rutas"]["candidato"].exists())
        ruta.write_bytes(original)

    def test_mejor_desempeno_tampoco_autoriza_publicacion(self):
        self.preparar()
        modelo = ajuste.SARIMAXResults.load(self.config["rutas"]["modelo_ajustado"])
        self.conjuntos["prueba"][self.config["columnas"]["valor"]] = np.exp(modelo.forecast(6)).to_numpy()
        self.guardar_fuentes()
        self.etapas_previas()
        self.preparar()
        reporte = self.exportar()
        self.assertTrue(reporte["supera_regla_desempeno"])
        self.assertFalse(reporte["publicacion_autorizada"])
        candidato = cargar_json(self.config["rutas"]["candidato"])
        self.assertEqual(candidato["estado_desempeno"], "supera_regla")
        self.assertFalse(candidato["publicacion_autorizada"])

    def test_peor_desempeno_queda_exportado_como_no_superado(self):
        self.preparar()
        self.conjuntos["prueba"][self.config["columnas"]["valor"]] = self.conjuntos["entrenamiento"][self.config["columnas"]["valor"]].iloc[24:30].to_numpy()
        self.guardar_fuentes()
        self.etapas_previas()
        self.preparar()
        reporte = self.exportar()
        self.assertEqual(reporte["estado"], "completada")
        self.assertFalse(reporte["supera_regla_desempeno"])
        candidato = cargar_json(self.config["rutas"]["candidato"])
        self.assertEqual(candidato["estado_desempeno"], "no_supera_regla")
        self.assertFalse(candidato["publicacion_autorizada"])

    def test_configuracion_cambiada_impide_exportar(self):
        self.preparar()
        self.ruta_config.write_text(self.ruta_config.read_text() + "\n# cambio posterior\n")
        with self.assertRaisesRegex(ValueError, "configuracion coincide"):
            self.exportar()
