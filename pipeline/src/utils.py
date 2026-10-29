"""Funciones compartidas de lectura, validacion y escritura del pipeline."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd


def huella_archivo(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def banner(titulo: str) -> None:
    print("=" * 60)
    print(titulo, flush=True)


def afirmar(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise ValueError(mensaje)
    print(f"[ok] {mensaje}", flush=True)


def cargar(ruta: Path, codificacion: str, separador: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Lee una copia de los bytes como texto y calcula su huella SHA-256."""
    contenido = ruta.read_bytes()
    encabezado = next(csv.reader(io.StringIO(contenido.decode(codificacion)), delimiter=separador), [])
    afirmar(bool(encabezado), f"{ruta.name}: el archivo tiene encabezados")
    afirmar(all(nombre.strip() for nombre in encabezado), f"{ruta.name}: no hay encabezados vacios")
    afirmar(len(set(encabezado)) == len(encabezado), f"{ruta.name}: los encabezados no se repiten")
    datos = pd.read_csv(
        io.BytesIO(contenido),
        encoding=codificacion,
        sep=separador,
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        skip_blank_lines=False,
        on_bad_lines="error",
    )
    afirmar(len(datos) > 0, f"{ruta.name}: contiene registros")
    afirmar(list(datos.columns) == encabezado, f"{ruta.name}: los encabezados se conservaron")
    print(f"[cargado] {ruta.name}: {len(datos):,} filas, {len(datos.columns)} columnas", flush=True)
    return datos, {
        "sha256": hashlib.sha256(contenido).hexdigest(),
        "bytes": len(contenido),
        "filas": len(datos),
        "columnas": list(datos.columns),
    }


def _escribir_atomico(ruta: Path, escritor: Any) -> None:
    """Reemplaza el destino solo cuando termino de escribirse el archivo nuevo."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    descriptor, nombre = tempfile.mkstemp(prefix=f".{ruta.name}.", suffix=".tmp", dir=ruta.parent)
    temporal = Path(nombre)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as archivo:
            escritor(archivo)
        os.replace(temporal, ruta)
    finally:
        temporal.unlink(missing_ok=True)
    print(f"[guardado] {ruta.name}", flush=True)


def guardar(datos: pd.DataFrame, ruta: Path, separador: str = ",") -> None:
    _escribir_atomico(ruta, lambda archivo: datos.to_csv(archivo, index=False, sep=separador, lineterminator="\n"))


def guardar_json(datos: Any, ruta: Path) -> None:
    def escribir(archivo: Any) -> None:
        json.dump(datos, archivo, ensure_ascii=False, indent=2, allow_nan=False)
        archivo.write("\n")

    _escribir_atomico(ruta, escribir)
