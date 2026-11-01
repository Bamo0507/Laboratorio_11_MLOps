"""Lista versiones aprobadas y reactiva una anterior cambiando solo el indicador vigente."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ARCHIVO_VIGENTE, CARPETA_VERSIONES, RUTA_CONFIGURACION, cargar_configuracion
from publicacion import bloqueo, consultar_vigente, preparar_version
from utils import afirmar, cargar_json, guardar_json

PATRON_PREFIJO = re.compile(r"[0-9a-f]{6,64}")


def listar(directorio: Path) -> list[dict[str, Any]]:
    vigente = consultar_vigente(directorio)
    versiones = []
    for archivo in (directorio / CARPETA_VERSIONES).glob("*.json"):
        contenido = cargar_json(archivo)
        versiones.append({"version": contenido["version"], "fecha_generacion": contenido["fecha_generacion"],
                          "id_ejecucion": contenido["id_ejecucion"], "mae": contenido["metricas"]["sarima"]["mae"],
                          "datos_sinteticos": contenido.get("datos_sinteticos", False),
                          "vigente": vigente is not None and vigente["version"] == contenido["version"]})
    return sorted(versiones, key=lambda v: v["fecha_generacion"])


def restaurar(directorio: Path, prefijo: str) -> dict[str, Any]:
    """Las versiones son inmutables: no se reescriben ni se borra la que estaba vigente."""
    afirmar(PATRON_PREFIJO.fullmatch(prefijo) is not None, "el identificador tiene al menos 6 caracteres hexadecimales")
    with bloqueo(directorio):
        anterior = consultar_vigente(directorio)
        archivos = list((directorio / CARPETA_VERSIONES).glob(f"{prefijo}*.json"))
        afirmar(len(archivos) == 1, f"{prefijo} identifica una sola version guardada")
        contenido = cargar_json(archivos[0])
        afirmar(contenido.get("version") == archivos[0].stem, "el contenido corresponde al nombre de la version")
        # Repite las comprobaciones de promocion sin escribir la version de nuevo.
        indicador = preparar_version(directorio, contenido)
        indicador.update(restaurada_utc=datetime.now(timezone.utc).isoformat(),
                         version_reemplazada=anterior["version"] if anterior else None)
        guardar_json(indicador, directorio / ARCHIVO_VIGENTE)
    afirmar(consultar_vigente(directorio)["version"] == indicador["version"], "el tablero consultara la version restaurada")
    return indicador


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--listar", action="store_true", help="Muestra las versiones aprobadas guardadas.")
    grupo.add_argument("--version", help="Identificador, o prefijo unico, de la version a reactivar.")
    argumentos = parser.parse_args()
    try:
        directorio = cargar_configuracion(argumentos.config)["rutas"]["publicaciones"]
        if argumentos.listar:
            for version in listar(directorio):
                print(json.dumps(version, ensure_ascii=False))
        else:
            indicador = restaurar(directorio, argumentos.version)
            print(f"[ok] Version vigente: {indicador['version']}. Reemplazo a: {indicador['version_reemplazada']}.")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"[FALLO] No se pudo restaurar: {error}\n")


if __name__ == "__main__":
    main()
