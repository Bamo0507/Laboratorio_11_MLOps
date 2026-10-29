"""Prepara la conexion local de MLflow sin registrar ejecuciones del pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

from config import (
    ARCHIVO_BASE_MLFLOW, CARPETA_ARTEFACTOS_MLFLOW,
    RUTA_CONFIGURACION, cargar_configuracion,
)
from utils import afirmar, banner


def conectar(configuracion: dict[str, Any]) -> tuple[MlflowClient, Any]:
    """Crea o recupera un experimento local con una ubicacion de archivos fija."""
    directorio = configuracion["rutas"]["mlflow"]
    base = directorio / ARCHIVO_BASE_MLFLOW
    artefactos = directorio / CARPETA_ARTEFACTOS_MLFLOW
    afirmar(base.resolve().is_relative_to(directorio) and artefactos.resolve().is_relative_to(directorio),
            "la base y los artefactos permanecen dentro de la carpeta de MLflow")
    directorio.mkdir(parents=True, exist_ok=True)
    # Las rutas absolutas se calculan aqui, no se guardan en el codigo o TOML.
    uri = f"sqlite:///{base.as_posix()}"
    cliente = MlflowClient(tracking_uri=uri, registry_uri=uri)
    nombre = configuracion["seguimiento"]["experimento"]
    experimento = cliente.get_experiment_by_name(nombre)
    if experimento is None:
        artefactos.mkdir(parents=True, exist_ok=True)
        try:
            identificador = cliente.create_experiment(nombre, artifact_location=artefactos.as_uri())
            experimento = cliente.get_experiment(identificador)
        except MlflowException as error:
            # Otro proceso local pudo crear el mismo experimento entre ambas llamadas.
            if error.error_code != "RESOURCE_ALREADY_EXISTS":
                raise
            experimento = cliente.get_experiment_by_name(nombre)
    afirmar(experimento is not None and experimento.lifecycle_stage == "active", "el experimento existe y esta activo")
    afirmar(experimento.artifact_location == artefactos.as_uri(),
            "los artefactos del experimento utilizan la carpeta local configurada; si se movio el proyecto, no reutilices una base copiada de otra ubicacion")
    artefactos.mkdir(parents=True, exist_ok=True)
    afirmar(base.is_file(), "la base SQLite fue creada y puede consultarse")
    return cliente, experimento


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION) -> dict[str, str]:
    configuracion = cargar_configuracion(ruta_configuracion)
    banner("Preparacion del seguimiento local")
    _, experimento = conectar(configuracion)
    resultado = {"experimento": experimento.name, "id_experimento": experimento.experiment_id}
    print(f"[ok] Experimento disponible: {experimento.name} (id {experimento.experiment_id}).")
    print("[ok] No se crearon ejecuciones ni se registraron modelos o metricas.")
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
    except (OSError, ValueError, TypeError, KeyError, MlflowException) as error:
        parser.exit(1, f"[FALLO] No se pudo preparar MLflow: {error}\n")


if __name__ == "__main__":
    main()
