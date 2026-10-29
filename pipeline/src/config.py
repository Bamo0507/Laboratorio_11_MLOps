"""Carga la configuracion y resuelve rutas sin depender de la computadora."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CONFIGURACION = RAIZ / "configuracion.toml"
PATRON_MES = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
SECCIONES = {"rutas", "ingesta", "periodos", "poblacion", "modelo", "referencia", "columnas"}


def resolver_ruta(raiz: Path, valor: str) -> Path:
    """Acepta rutas relativas contenidas en la carpeta del pipeline."""
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError("Cada ruta debe ser un texto no vacio.")
    relativa = Path(valor)
    if relativa.is_absolute() or PureWindowsPath(valor).anchor:
        raise ValueError(f"La ruta debe ser relativa, no absoluta: {valor}")
    if "\\" in valor:
        raise ValueError(f"Usa / como separador portable de carpetas: {valor}")
    resuelta = (raiz / relativa).resolve()
    if not resuelta.is_relative_to(raiz.resolve()):
        raise ValueError(f"La ruta debe permanecer dentro del pipeline: {valor}")
    return resuelta


def validar_periodos(periodos: dict[str, str]) -> None:
    claves = ("inicio_ajuste", "fin_ajuste", "inicio_evaluacion", "fin_evaluacion")
    for clave in claves:
        valor = periodos.get(clave)
        if not isinstance(valor, str) or not PATRON_MES.fullmatch(valor):
            raise ValueError(f"{clave} debe tener formato AAAA-MM.")
        date.fromisoformat(f"{valor}-01")
    if not (
        periodos["inicio_ajuste"] <= periodos["fin_ajuste"]
        < periodos["inicio_evaluacion"] <= periodos["fin_evaluacion"]
    ):
        raise ValueError("El ajuste debe preceder a la evaluacion, sin solaparse.")


def cargar_configuracion(ruta: Path | None = None) -> dict[str, Any]:
    """Lee TOML y devuelve las rutas calculadas para esta copia del proyecto."""
    ruta = Path(ruta or RUTA_CONFIGURACION).resolve()
    with ruta.open("rb") as archivo:
        configuracion = tomllib.load(archivo)
    faltantes = SECCIONES - configuracion.keys()
    if faltantes:
        raise ValueError(f"Faltan secciones de configuracion: {sorted(faltantes)}")

    raiz = ruta.parent
    rutas = configuracion["rutas"]
    for clave in ("entrenamiento", "prueba", "procesados", "publicaciones", "mlflow", "ingesta", "reporte_ingesta"):
        if clave not in rutas:
            raise ValueError(f"Falta la ruta {clave}.")
        rutas[clave] = resolver_ruta(raiz, rutas[clave])

    entradas = [rutas["entrenamiento"], rutas["prueba"]]
    if entradas[0] == entradas[1]:
        raise ValueError("Entrenamiento y prueba deben ser archivos diferentes.")
    if any(entrada.is_relative_to(rutas["procesados"]) for entrada in entradas):
        raise ValueError("Los insumos no pueden estar en la carpeta de resultados.")
    for clave in ("publicaciones", "mlflow", "ingesta", "reporte_ingesta"):
        if not rutas[clave].is_relative_to(rutas["procesados"]):
            raise ValueError(f"La ruta {clave} debe estar dentro de procesados.")
    salidas = (rutas["ingesta"], rutas["reporte_ingesta"])
    if salidas[0] == salidas[1] or any(salida == rutas["procesados"] for salida in salidas):
        raise ValueError("La ingesta y su reporte deben ser archivos diferentes.")

    ingesta = configuracion["ingesta"]
    for clave in ("codificacion", "separador", "columna_origen"):
        if not isinstance(ingesta.get(clave), str) or not ingesta[clave].strip():
            raise ValueError(f"ingesta.{clave} debe ser un texto no vacio.")
    if len(ingesta["separador"]) != 1:
        raise ValueError("El separador CSV debe tener un solo caracter.")

    validar_periodos(configuracion["periodos"])
    modelo = configuracion["modelo"]
    for clave, longitud in (("orden", 3), ("orden_estacional", 4)):
        valores = modelo.get(clave)
        if not isinstance(valores, list) or len(valores) != longitud:
            raise ValueError(f"{clave} debe tener {longitud} valores.")
        if any(type(v) is not int or v < 0 for v in valores):
            raise ValueError(f"{clave} solo admite enteros no negativos.")
    if modelo["orden_estacional"][-1] < 2:
        raise ValueError("La periodicidad estacional debe ser al menos 2.")
    rezago = configuracion["referencia"].get("rezago_meses")
    if type(rezago) is not int or rezago < 1:
        raise ValueError("El rezago de referencia debe ser un entero positivo.")
    return configuracion


def columnas_requeridas(configuracion: dict[str, Any]) -> list[str]:
    """Columnas necesarias para analizar la serie y comprobar la granularidad."""
    columnas = configuracion["columnas"]
    nombres = [columnas[k] for k in ("fecha", "anio", "mes", "pais", "tipo", "valor")]
    nombres.extend(columnas["clave_registro"])
    if any(not isinstance(nombre, str) or not nombre for nombre in nombres):
        raise ValueError("Los nombres de columna deben ser textos no vacios.")
    return list(dict.fromkeys(nombres))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        configuracion = cargar_configuracion(argumentos.config)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"[FALLO] {error}\n")
    print("[ok] Configuracion cargada. No se ejecutaron etapas ni se modificaron datos.")
    print(json.dumps(configuracion, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
