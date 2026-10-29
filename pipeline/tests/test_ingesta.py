"""Comprueba preservacion de datos y detencion de la ingesta ante insumos invalidos."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
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

spec = importlib.util.spec_from_file_location("etapa_ingesta", RAIZ / "src/01_ingesta.py")
ingesta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingesta)


def huella(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


class PruebasIngesta(unittest.TestCase):
    def setUp(self) -> None:
        self.temporal = tempfile.TemporaryDirectory(prefix="lab11_ingesta_")
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.ruta_config = self.raiz / "configuracion.toml"
        self.ruta_config.write_bytes((RAIZ / "configuracion.toml").read_bytes())
        self.config = cargar_configuracion(self.ruta_config)
        self.columnas = columnas_requeridas(self.config) + ["observacion"]
        for clave in ("entrenamiento", "prueba"):
            ruta = self.config["rutas"][clave]
            ruta.parent.mkdir(parents=True, exist_ok=True)
            with ruta.open("w", encoding="utf-8", newline="") as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(self.columnas)
                for valor in ("0007", "NA", "NaN", ""):
                    fila = {columna: "dato" for columna in self.columnas}
                    fila["observacion"] = valor
                    escritor.writerow([fila[columna] for columna in self.columnas])

    def ejecutar(self) -> dict:
        with redirect_stdout(StringIO()):
            return ingesta.ejecutar(self.ruta_config)

    def salida_previa(self) -> dict[str, str]:
        self.ejecutar()
        return {clave: huella(self.config["rutas"][clave]) for clave in ("ingesta", "reporte_ingesta")}

    def comprobar_salida_conservada(self, anterior: dict[str, str]) -> None:
        for clave, valor in anterior.items():
            self.assertEqual(huella(self.config["rutas"][clave]), valor)

    def test_preserva_textos_vacios_procedencia_y_fuentes(self) -> None:
        fuentes = {clave: huella(self.config["rutas"][clave]) for clave in ("entrenamiento", "prueba")}
        reporte = self.ejecutar()
        datos = pd.read_csv(self.config["rutas"]["ingesta"], dtype=str, na_filter=False)
        self.assertEqual(datos["observacion"].tolist(), ["0007", "NA", "NaN", ""] * 2)
        self.assertEqual(len(datos), 8)
        self.assertEqual(datos["archivo_origen"].value_counts().tolist(), [4, 4])
        self.assertEqual(reporte["filas_salida"], 8)
        for clave, valor in fuentes.items():
            self.assertEqual(huella(self.config["rutas"][clave]), valor)
        self.assertEqual(reporte, json.loads(self.config["rutas"]["reporte_ingesta"].read_text()))

    def test_repetir_produce_los_mismos_archivos(self) -> None:
        anterior = self.salida_previa()
        self.ejecutar()
        self.comprobar_salida_conservada(anterior)

    def test_columna_ausente_no_reemplaza_salidas(self) -> None:
        anterior = self.salida_previa()
        ruta = self.config["rutas"]["prueba"]
        datos = pd.read_csv(ruta, dtype=str, na_filter=False).drop(columns=[self.config["columnas"]["pais"]])
        datos.to_csv(ruta, index=False)
        with self.assertRaisesRegex(ValueError, "columnas indispensables"):
            self.ejecutar()
        self.comprobar_salida_conservada(anterior)

    def test_encabezado_repetido_no_reemplaza_salidas(self) -> None:
        anterior = self.salida_previa()
        self.config["rutas"]["prueba"].write_text("Fecha,Fecha\n2026-01,2026-01\n")
        with self.assertRaisesRegex(ValueError, "encabezados no se repiten"):
            self.ejecutar()
        self.comprobar_salida_conservada(anterior)

    def test_orquestador_falla_desde_otro_directorio_sin_reemplazar_salidas(self) -> None:
        anterior = self.salida_previa()
        self.config["rutas"]["prueba"].unlink()
        resultado = subprocess.run(
            [sys.executable, str(RAIZ / "src/run_pipeline.py"), "--config", str(self.ruta_config)],
            cwd=self.raiz,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("El pipeline se detuvo en 01_ingesta.py", resultado.stderr)
        self.comprobar_salida_conservada(anterior)


if __name__ == "__main__":
    unittest.main()
