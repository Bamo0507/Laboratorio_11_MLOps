"""Etapa 0: crear el entorno virtual e instalar las dependencias fijadas.

Ejecutar desde la raiz del repositorio: python3.13 pipeline/src/00_init.py
"""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIR_ENTORNO = RAIZ / ".venv"
RUTA_REQUIREMENTS = RAIZ / "requirements.txt"
VERSION_PYTHON = (3, 13)


def main() -> None:
    if sys.version_info[:2] != VERSION_PYTHON:
        raise ValueError(
            "Este pipeline utiliza Python 3.13. Ejecuta python3.13 "
            "pipeline/src/00_init.py, o py -3.13 pipeline/src/00_init.py en Windows."
        )
    if not RUTA_REQUIREMENTS.is_file():
        raise FileNotFoundError(f"No se encontro {RUTA_REQUIREMENTS.name}.")

    if not DIR_ENTORNO.exists():
        print("[creando] Entorno virtual del pipeline", flush=True)
        venv.EnvBuilder(with_pip=True).create(DIR_ENTORNO)

    ejecutable = DIR_ENTORNO / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    if not ejecutable.is_file():
        raise ValueError("La carpeta .venv existe, pero no contiene un Python utilizable.")
    version = subprocess.check_output(
        [str(ejecutable), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        text=True,
    ).strip()
    if version != ".".join(map(str, VERSION_PYTHON)):
        raise ValueError("El entorno existente no utiliza Python 3.13. No se modifico.")

    print("[instalando] Versiones fijadas en requirements.txt", flush=True)
    subprocess.run(
        [str(ejecutable), "-m", "pip", "--disable-pip-version-check", "install", "-r", str(RUTA_REQUIREMENTS)],
        check=True,
    )
    subprocess.run([str(ejecutable), "-m", "pip", "check"], check=True)
    print("[ok] Entorno preparado. Los datos y los modelos no se modificaron.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"[FALLO] {error}") from error
