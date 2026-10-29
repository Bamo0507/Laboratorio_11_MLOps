"""Ejecuta en orden las etapas implementadas y se detiene ante el primer fallo."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from config import RUTA_CONFIGURACION

DIR_SRC = Path(__file__).resolve().parent
ETAPAS = ["01_ingesta.py", "02_validacion.py", "03_preparacion.py", "04_ajuste.py", "05_evaluacion.py", "06_exportacion.py"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    for etapa in ETAPAS:
        resultado = subprocess.run(
            [sys.executable, str(DIR_SRC / etapa), "--config", str(argumentos.config.resolve())],
            check=False,
        )
        if resultado.returncode:
            parser.exit(resultado.returncode, f"[FALLO] El pipeline se detuvo en {etapa}.\n")
    print("[ok] Ingesta, validacion, preparacion, ajuste, evaluacion y exportacion candidata completados. El registro en MLflow y la publicacion siguen pendientes.")


main()
