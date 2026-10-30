"""Publicacion condicionada, versiones inmutables y conservacion ante fallos."""

import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import numpy as np

import test_ajuste as apoyo
from test_ajuste import ajuste, cargar_etapa
from config import ARCHIVO_BLOQUEO_PUBLICACION, ARCHIVO_VIGENTE, CARPETA_VERSIONES
from publicacion import consultar_vigente
from utils import cargar_json, guardar_json, huella_archivo

evaluacion = cargar_etapa("05_evaluacion")
exportacion = cargar_etapa("06_exportacion")
publicacion = cargar_etapa("07_publicacion")


class PruebasPublicacion(unittest.TestCase):
    setUp = apoyo.PruebasAjuste.setUp
    guardar_fuentes = apoyo.PruebasAjuste.guardar_fuentes
    etapas_previas = apoyo.PruebasAjuste.etapas_previas

    def preparar(self, favorable=True):
        with redirect_stdout(StringIO()):
            ajuste.ejecutar(self.ruta_config)
            if favorable:
                modelo = ajuste.SARIMAXResults.load(self.config["rutas"]["modelo_ajustado"])
                valores = np.exp(modelo.forecast(6)).to_numpy()
            else:
                valores = self.conjuntos["entrenamiento"][self.config["columnas"]["valor"]].iloc[24:30].to_numpy()
            self.conjuntos["prueba"][self.config["columnas"]["valor"]] = valores
            self.guardar_fuentes()
            self.etapas_previas()
            ajuste.ejecutar(self.ruta_config)
            evaluacion.ejecutar(self.ruta_config)
            exportacion.ejecutar(self.ruta_config)

    def ejecutar(self):
        with redirect_stdout(StringIO()):
            return publicacion.ejecutar(self.ruta_config)

    def vigente(self):
        with redirect_stdout(StringIO()):
            return consultar_vigente(self.config["rutas"]["publicaciones"])

    def ruta_vigente(self):
        return self.config["rutas"]["publicaciones"] / ARCHIVO_VIGENTE

    def test_sin_primera_aprobacion_no_hay_estimaciones_disponibles(self):
        self.preparar(False)
        reporte = self.ejecutar()
        self.assertEqual(reporte["estado"], "no_publicado")
        self.assertEqual(reporte["criterios_aceptacion"], {"calidad": True, "integridad": True, "observaciones_comparables": True, "desempeno": False})
        self.assertFalse(reporte["estimaciones_disponibles"])
        self.assertFalse(self.ruta_vigente().exists())
        self.assertIsNone(self.vigente())

    def test_publica_y_repetir_mismo_candidato_no_duplica_version(self):
        self.preparar()
        reporte = self.ejecutar()
        version = self.vigente()
        self.assertTrue(reporte["publicacion_autorizada"])
        self.assertTrue(all(reporte["criterios_aceptacion"].values()))
        self.assertEqual(reporte["version_vigente"], version["version"])
        self.assertEqual(len(version["estimaciones"]), 6)
        for fila in version["estimaciones"]:
            self.assertEqual(fila["destino"], "Guatemala")
            self.assertEqual(fila["unidad"], "llegadas_por_mes")
            self.assertEqual(fila["valor"], fila["sarima"])
            self.assertEqual(fila["id_ejecucion_local"], version["id_ejecucion_local"])
        anterior = huella_archivo(self.ruta_vigente())
        self.ejecutar()
        self.assertEqual(anterior, huella_archivo(self.ruta_vigente()))
        self.assertEqual(len(list((self.config["rutas"]["publicaciones"] / CARPETA_VERSIONES).glob("*.json"))), 1)

    def test_desempeno_desfavorable_conserva_version_anterior(self):
        self.preparar()
        self.ejecutar()
        anterior = huella_archivo(self.ruta_vigente())
        version = self.vigente()
        self.preparar(False)
        reporte = self.ejecutar()
        self.assertEqual(reporte["estado"], "no_publicado")
        self.assertTrue(reporte["estimaciones_disponibles"])
        self.assertEqual(anterior, huella_archivo(self.ruta_vigente()))
        self.assertEqual(version, self.vigente())

    def test_nueva_aprobacion_conserva_version_anterior_en_disco(self):
        self.preparar()
        self.ejecutar()
        primero = self.vigente()
        with redirect_stdout(StringIO()):
            exportacion.ejecutar(self.ruta_config)
        reporte = self.ejecutar()
        self.assertNotEqual(primero["version"], reporte["version_vigente"])
        ruta = self.config["rutas"]["publicaciones"] / CARPETA_VERSIONES / f"{primero['version']}.json"
        self.assertEqual(cargar_json(ruta), primero)
        self.assertEqual(reporte["version_anterior"], primero["version"])

    def test_datos_alterados_y_candidato_alterado_no_reemplazan_vigente(self):
        self.preparar()
        self.ejecutar()
        anterior = huella_archivo(self.ruta_vigente())
        for nombre in ("entrenamiento", "prueba", "candidato", "reporte_evaluacion", "modelo_ajustado"):
            ruta = self.config["rutas"][nombre]
            original = ruta.read_bytes()
            ruta.write_bytes(original + b"\n")
            with self.assertRaises(ValueError):
                self.ejecutar()
            self.assertEqual(anterior, huella_archivo(self.ruta_vigente()))
            self.assertEqual(cargar_json(self.config["rutas"]["reporte_publicacion"])["estado"], "rechazado")
            ruta.write_bytes(original)

    def test_fallo_al_activar_o_guardar_reporte_conserva_vigente(self):
        self.preparar()
        self.ejecutar()
        anterior = huella_archivo(self.ruta_vigente())
        with redirect_stdout(StringIO()):
            exportacion.ejecutar(self.ruta_config)
        for objetivo in (self.ruta_vigente(), self.config["rutas"]["reporte_publicacion"]):
            def fallo(datos, ruta):
                if ruta == objetivo:
                    raise OSError("Fallo de escritura simulado")
                return guardar_json(datos, ruta)
            with patch.object(publicacion, "guardar_json", side_effect=fallo), self.assertRaises(OSError):
                self.ejecutar()
            self.assertEqual(anterior, huella_archivo(self.ruta_vigente()))

    def test_bloqueo_existente_no_se_borra_y_no_se_publica(self):
        self.preparar()
        directorio = self.config["rutas"]["publicaciones"]
        directorio.mkdir(parents=True)
        bloqueo = directorio / ARCHIVO_BLOQUEO_PUBLICACION
        bloqueo.write_text("otro proceso")
        with self.assertRaises(FileExistsError):
            self.ejecutar()
        self.assertEqual(bloqueo.read_text(), "otro proceso")
        self.assertFalse(self.ruta_vigente().exists())

    def test_consulta_rechaza_version_corrupta_y_rutas_fuera_del_directorio(self):
        self.preparar()
        self.ejecutar()
        indicador = cargar_json(self.ruta_vigente())
        archivo = self.config["rutas"]["publicaciones"] / indicador["archivo"]
        original = archivo.read_bytes()
        archivo.write_bytes(original + b"\n")
        with self.assertRaises(ValueError):
            self.vigente()
        archivo.write_bytes(original)
        indicador["archivo"] = "../candidato.json"
        guardar_json(indicador, self.ruta_vigente())
        with self.assertRaises(ValueError):
            self.vigente()
