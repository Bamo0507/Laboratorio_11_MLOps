"""Monitoreo de resultados y calidad, y restauracion de versiones aprobadas."""

import unittest
from contextlib import redirect_stdout
from io import StringIO

import test_ajuste as apoyo
import test_publicacion as base
from test_ajuste import cargar_etapa
from config import ARCHIVO_VIGENTE
from restaurar import restaurar
from utils import cargar_json, guardar_json, huella_archivo

monitoreo = cargar_etapa("08_monitoreo")


class PruebasMonitoreo(unittest.TestCase):
    def silencio(self, funcion, *argumentos):
        with redirect_stdout(StringIO()):
            return funcion(*argumentos)

    def test_resultados_alerta_negativos_no_finitos_y_variacion_elevada(self):
        filas = [{"fecha": "2026-01-01", "sarima": 140.0, "referencia": 100.0},
                 {"fecha": "2026-02-01", "sarima": -1.0, "referencia": 100.0},
                 {"fecha": "2026-03-01", "sarima": float("inf"), "referencia": 100.0},
                 {"fecha": "2026-04-01", "sarima": 125.0, "referencia": 100.0}]
        resultado = self.silencio(monitoreo.verificar_resultados, filas, 0.30)
        self.assertEqual(resultado["estado"], "alerta")
        self.assertEqual([a[:7] for a in resultado["alertas"]], ["2026-01", "2026-02", "2026-03"])

    def test_calidad_compara_con_el_monitoreo_anterior(self):
        anterior = {"filas": 10, "faltantes": 0, "duplicados_completos": 0, "coincidencias_parciales": 0, "meses_sin_cobertura": 0}
        self.assertEqual(self.silencio(monitoreo.verificar_calidad, anterior, None)["estado"], "ok")
        self.assertEqual(self.silencio(monitoreo.verificar_calidad, {**anterior, "filas": 12}, anterior)["estado"], "ok")
        peor = {**anterior, "filas": 9, "coincidencias_parciales": 1}
        self.assertEqual(len(self.silencio(monitoreo.verificar_calidad, peor, anterior)["alertas"]), 2)
        self.assertEqual(self.silencio(monitoreo.verificar_calidad, None, anterior)["estado"], "alerta")


class PruebasRestauracion(unittest.TestCase):
    setUp = apoyo.PruebasAjuste.setUp
    guardar_fuentes = apoyo.PruebasAjuste.guardar_fuentes
    etapas_previas = apoyo.PruebasAjuste.etapas_previas
    preparar = base.PruebasPublicacion.preparar
    ejecutar = base.PruebasPublicacion.ejecutar
    vigente = base.PruebasPublicacion.vigente

    def test_monitoreo_y_restauracion_de_la_version_anterior(self):
        self.preparar()
        self.ejecutar()
        primera = self.vigente()["version"]
        with redirect_stdout(StringIO()):
            reporte = monitoreo.ejecutar(self.ruta_config)
        estados = {v["codigo"]: v["estado"] for v in reporte["verificaciones"]}
        self.assertEqual(estados["actualizacion"], "ok")
        self.assertIsNotNone(reporte["error_predictivo"])
        self.preparar()
        self.ejecutar()
        segunda = self.vigente()["version"]
        self.assertNotEqual(primera, segunda)
        directorio = self.config["rutas"]["publicaciones"]
        with redirect_stdout(StringIO()):
            indicador = restaurar(directorio, primera[:8])
        self.assertEqual(self.vigente()["version"], primera)
        self.assertEqual(indicador["version_reemplazada"], segunda)
        # Una version alterada no se reactiva y el indicador vigente no cambia.
        archivo = directorio / "versiones" / f"{segunda}.json"
        guardar_json({**cargar_json(archivo), "publicacion_autorizada": False}, archivo)
        antes = huella_archivo(directorio / ARCHIVO_VIGENTE)
        with redirect_stdout(StringIO()), self.assertRaises(ValueError):
            restaurar(directorio, segunda)
        with redirect_stdout(StringIO()), self.assertRaises(ValueError):
            restaurar(directorio, "*")
        self.assertEqual(huella_archivo(directorio / ARCHIVO_VIGENTE), antes)
        self.assertFalse((directorio / ".publicacion.lock").exists())


if __name__ == "__main__":
    unittest.main()
