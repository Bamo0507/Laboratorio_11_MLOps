"""Ejecuta el pipeline y registra datos, codigo, parametros y resultados en MLflow."""

import argparse
import subprocess
from pathlib import Path

from mlflow.exceptions import MlflowException

from config import RUTA_CONFIGURACION
from orquestacion import ejecutar

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
argumentos = parser.parse_args()
try:
    identificador = ejecutar(argumentos.config)
except (OSError, ValueError, TypeError, KeyError, MlflowException, subprocess.CalledProcessError) as error:
    if isinstance(error, subprocess.CalledProcessError):
        parser.exit(1, f"[FALLO] El pipeline se detuvo en {error.cmd[0]}.\n")
    parser.exit(1, f"[FALLO] No se pudo completar el pipeline: {error}\n")
print(f"[ok] Pipeline registrado en MLflow: {identificador}. La decision de publicacion se conserva por separado del estado de ejecucion.")
