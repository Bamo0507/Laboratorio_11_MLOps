"""Encadena las etapas y recoge exclusivamente los resultados del run actual."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from config import RUTA_CONFIGURACION, cargar_configuracion
from registro_mlflow import registrar_etapa, registrar_fallo_etapa
from seguimiento import registrar_ejecucion

DIR_SRC = Path(__file__).resolve().parent
ETAPAS = ["01_ingesta.py", "02_validacion.py", "03_preparacion.py", "04_ajuste.py", "05_evaluacion.py", "06_exportacion.py", "07_publicacion.py"]


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION, destino_seguimiento: dict | None = None, tipo: str = "pipeline") -> str:
    ruta_configuracion = Path(ruta_configuracion).resolve()
    configuracion = cargar_configuracion(ruta_configuracion)
    with registrar_ejecucion(configuracion, ruta_configuracion, destino_seguimiento, tipo) as registro:
        for etapa in ETAPAS:
            registro.iniciar_etapa(etapa)
            ruta_calidad = configuracion["rutas"]["reporte_validacion"]
            anterior = (ruta_calidad.stat().st_mtime_ns, ruta_calidad.stat().st_size) if ruta_calidad.exists() else None
            comando = [sys.executable, str(DIR_SRC / etapa), "--config", str(ruta_configuracion)]
            if etapa == "06_exportacion.py":
                comando.extend(["--id-ejecucion-mlflow", registro.id_ejecucion])
            resultado = subprocess.run(comando, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace",
                                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            print(resultado.stdout, end="", flush=True)
            registro.cliente.log_text(registro.id_ejecucion, resultado.stdout, f"logs/{etapa}.txt")
            if resultado.returncode:
                registrar_fallo_etapa(registro, configuracion, etapa, anterior)
                raise subprocess.CalledProcessError(resultado.returncode, [etapa], output=resultado.stdout)
            registrar_etapa(registro, configuracion, etapa)
            registro.completar_etapa(etapa)
    return registro.id_ejecucion
