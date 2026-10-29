"""Consulta y promocion atomica de versiones aprobadas en almacenamiento local."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any
import re

from config import ARCHIVO_BLOQUEO_PUBLICACION, ARCHIVO_VIGENTE, CARPETA_VERSIONES
from utils import afirmar, cargar_json, guardar_json, huella_archivo

PATRON_VERSION = re.compile(r"[0-9a-f]{64}")


@contextmanager
def bloqueo(directorio: Path):
    """Impide dos escritores simultaneos; no elimina bloqueos de otros procesos."""
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / ARCHIVO_BLOQUEO_PUBLICACION
    with ruta.open("x", encoding="utf-8") as archivo:
        archivo.write("Publicacion en curso.\n")
    try:
        yield
    finally:
        ruta.unlink()


def consultar_vigente(directorio: Path) -> dict[str, Any] | None:
    """La ausencia de vigente significa no disponible, sin recurrir al candidato."""
    ruta = directorio / ARCHIVO_VIGENTE
    if not ruta.exists():
        return None
    indicador = cargar_json(ruta)
    version = indicador.get("version", "")
    afirmar(isinstance(version, str) and PATRON_VERSION.fullmatch(version) is not None, "el identificador de la version vigente es valido")
    relativa = Path(CARPETA_VERSIONES) / f"{version}.json"
    afirmar(indicador.get("archivo") == relativa.as_posix(), "la version vigente utiliza la ruta esperada")
    archivo = (directorio / relativa).resolve()
    afirmar(archivo.is_relative_to(directorio.resolve()), "la version vigente permanece dentro de publicaciones")
    afirmar(indicador.get("sha256") == huella_archivo(archivo), "la version vigente conserva su integridad")
    contenido = cargar_json(archivo)
    afirmar(contenido.get("version") == version and contenido.get("publicacion_autorizada") is True, "la version vigente fue aprobada")
    return contenido


def preparar_version(directorio: Path, contenido: dict[str, Any]) -> dict[str, Any]:
    """Guarda una version inmutable y devuelve el indicador listo para activar."""
    version = contenido["version"]
    afirmar(PATRON_VERSION.fullmatch(version) is not None, "el identificador de la nueva version es valido")
    afirmar(contenido.get("publicacion_autorizada") is True, "solo se promueven versiones aprobadas")
    versiones = directorio / CARPETA_VERSIONES
    afirmar(versiones.resolve().is_relative_to(directorio.resolve()), "las versiones permanecen dentro de publicaciones")
    archivo = versiones / f"{version}.json"
    afirmar(archivo.resolve().is_relative_to(directorio.resolve()), "el archivo de version permanece dentro de publicaciones")
    if archivo.exists():
        afirmar(cargar_json(archivo) == contenido, "la version existente conserva exactamente su contenido")
    else:
        guardar_json(contenido, archivo)
    afirmar(cargar_json(archivo) == contenido, "la nueva version guardada conserva su contenido")
    indicador = {"version": version, "archivo": archivo.relative_to(directorio).as_posix(),
                 "sha256": huella_archivo(archivo), "fecha_generacion": contenido["fecha_generacion"]}
    return indicador
