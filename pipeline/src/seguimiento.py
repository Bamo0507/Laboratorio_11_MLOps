"""Conexion SQLite y seguimiento del inicio, las etapas y el cierre del pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


@dataclass
class RegistroEjecucion:
    cliente: MlflowClient
    id_ejecucion: str
    etapas_completadas: list[str] = field(default_factory=list)
    fuentes: list[dict] = field(default_factory=list)

    def iniciar_etapa(self, etapa: str) -> None:
        self.cliente.set_tag(self.id_ejecucion, "etapa_actual", etapa)
        self.cliente.set_tag(self.id_ejecucion, f"etapa.{etapa}.estado", "en_curso")

    def completar_etapa(self, etapa: str) -> None:
        self.cliente.set_tag(self.id_ejecucion, f"etapa.{etapa}.estado", "completada")
        self.etapas_completadas.append(etapa)
        self.cliente.set_tag(self.id_ejecucion, "etapas_completadas", json.dumps(self.etapas_completadas))


@contextmanager
def registrar_ejecucion(configuracion: dict[str, Any], ruta_configuracion: Path | None = None, destino_seguimiento: dict | None = None, tipo: str = "pipeline"):
    """Un run por invocacion; no lee metricas ni reportes de ejecuciones previas."""
    cliente, experimento = conectar(destino_seguimiento or configuracion)
    inicio = datetime.now(timezone.utc).isoformat()
    run = cliente.create_run(experimento.experiment_id, tags={
        "destino": configuracion["poblacion"]["destino"],
        "inicio_utc": inicio, "etapas_completadas": "[]",
        "publicacion": "no_evaluada", "alcance_registro": "completo" if ruta_configuracion else "ciclo_de_vida",
        "tipo_ejecucion": tipo,
    }, run_name=f"pipeline_{inicio}")
    registro = RegistroEjecucion(cliente, run.info.run_id)
    print(f"[ok] Ejecucion MLflow iniciada: {registro.id_ejecucion}", flush=True)
    try:
        if ruta_configuracion is not None:
            from registro_mlflow import registrar_inicio
            registrar_inicio(registro, configuracion, ruta_configuracion)
        yield registro
    except BaseException as error:
        estado = "KILLED" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "FAILED"
        # El final de la salida del subproceso incluye la causa informada por la etapa.
        detalle = getattr(error, "output", None) or str(error)
        cliente.set_tag(registro.id_ejecucion, "error_tipo", type(error).__name__)
        cliente.set_tag(registro.id_ejecucion, "error_causa", str(detalle)[-4000:])
        actual = cliente.get_run(registro.id_ejecucion).data.tags.get("etapa_actual")
        if actual and actual not in registro.etapas_completadas:
            cliente.set_tag(registro.id_ejecucion, f"etapa.{actual}.estado", "interrumpida" if estado == "KILLED" else "fallida")
        cliente.log_dict(registro.id_ejecucion, {"tipo": type(error).__name__, "causa": str(detalle), "etapa": actual, "etapas_completadas": registro.etapas_completadas}, "ejecucion/error.json")
        cliente.set_tag(registro.id_ejecucion, "fin_utc", datetime.now(timezone.utc).isoformat())
        cliente.set_terminated(registro.id_ejecucion, status=estado)
        print(f"[FALLO] Ejecucion MLflow {registro.id_ejecucion}: {estado}.", flush=True)
        raise
    else:
        cliente.set_tag(registro.id_ejecucion, "fin_utc", datetime.now(timezone.utc).isoformat())
        cliente.set_terminated(registro.id_ejecucion, status="FINISHED")
        print(f"[ok] Ejecucion MLflow {registro.id_ejecucion}: FINISHED.", flush=True)


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
    parser.add_argument("--interfaz", action="store_true", help="Abre el servicio local para consultar los runs en el navegador.")
    parser.add_argument("--puerto", type=int, default=5000)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
        if argumentos.interfaz:
            if not 1 <= argumentos.puerto <= 65535:
                raise ValueError("El puerto debe estar entre 1 y 65535.")
            configuracion = cargar_configuracion(argumentos.config)
            base = configuracion["rutas"]["mlflow"] / ARCHIVO_BASE_MLFLOW
            print(f"[ok] Interfaz local en http://127.0.0.1:{argumentos.puerto}. Detener con Ctrl+C.", flush=True)
            subprocess.run([sys.executable, "-m", "mlflow", "server", "--backend-store-uri", f"sqlite:///{base.as_posix()}",
                            "--host", "127.0.0.1", "--port", str(argumentos.puerto)], check=True)
    except (OSError, ValueError, TypeError, KeyError, MlflowException, subprocess.CalledProcessError) as error:
        parser.exit(1, f"[FALLO] No se pudo preparar MLflow: {error}\n")


if __name__ == "__main__":
    main()
