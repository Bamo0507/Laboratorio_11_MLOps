"""
Etapa 1 del pipeline: INGESTA
------------------------------------------------------------
Una sola responsabilidad: reunir los dos CSV conservando sus valores originales.

  Lee : las rutas de entrenamiento y prueba de configuracion.toml
  Hace: - carga los valores como texto, sin imputar ni convertir tipos
        - comprueba columnas y conserva la procedencia de cada fila
        - registra huellas SHA-256 y conteos de los archivos leidos
  Escribe: las rutas ingesta y reporte_ingesta de la configuracion

Ejecutar: python pipeline/src/01_ingesta.py
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from config import RUTA_CONFIGURACION, cargar_configuracion, columnas_requeridas
from utils import afirmar, banner, cargar, guardar, guardar_json


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION) -> dict[str, Any]:
    configuracion = cargar_configuracion(ruta_configuracion)
    rutas, opciones = configuracion["rutas"], configuracion["ingesta"]
    requeridas = set(columnas_requeridas(configuracion))
    columna_origen = opciones["columna_origen"]
    conjuntos: list[pd.DataFrame] = []
    fuentes: list[dict[str, Any]] = []
    columnas: list[str] | None = None
    raiz = Path(ruta_configuracion).resolve().parent
    banner("Etapa 1: ingesta")

    for clave in ("entrenamiento", "prueba"):
        datos, metadatos = cargar(rutas[clave], opciones["codificacion"], opciones["separador"])
        faltantes = requeridas - set(datos.columns)
        afirmar(not faltantes, f"{clave}: columnas indispensables presentes; faltan {sorted(faltantes)}")
        afirmar(columna_origen not in datos.columns, f"{clave}: la columna de procedencia no sobrescribe datos")
        if columnas is None:
            columnas = list(datos.columns)
        afirmar(set(datos.columns) == set(columnas), f"{clave}: los dos insumos tienen las mismas columnas")
        datos = datos[columnas].copy()
        origen = rutas[clave].relative_to(raiz).as_posix()
        datos[columna_origen] = origen
        conjuntos.append(datos)
        fuentes.append({"archivo": origen, **metadatos})

    unidos = pd.concat(conjuntos, ignore_index=True)
    total = sum(fuente["filas"] for fuente in fuentes)
    afirmar(len(unidos) == total, f"se conservaron las {total:,} filas de entrada")
    afirmar(list(unidos.columns) == [*columnas, columna_origen], "la salida conserva las columnas y agrega procedencia")
    reporte = {
        "etapa": "01_ingesta",
        "estado": "completada",
        "fuentes": fuentes,
        "filas_salida": len(unidos),
        "columnas_salida": list(unidos.columns),
        "salida": rutas["ingesta"].relative_to(raiz).as_posix(),
        "codificacion_salida": "utf-8",
        "separador_salida": opciones["separador"],
        "faltantes": "conservados como texto; no se aplicaron conversiones ni imputaciones",
    }
    guardar(unidos, rutas["ingesta"], separador=opciones["separador"])
    guardar_json(reporte, rutas["reporte_ingesta"])
    return reporte


def main() -> None:
    parser = argparse.ArgumentParser(description="Reunir los CSV sin modificar sus valores.")
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
        parser.exit(1, f"[FALLO] Ingesta detenida: {error}\n")


if __name__ == "__main__":
    main()
