"""Carga la configuracion y resuelve rutas sin depender de la computadora."""

from __future__ import annotations

import argparse
import json
import math
import re
import tomllib
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
RUTA_CONFIGURACION = RAIZ / "configuracion.toml"
PATRON_MES = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
SECCIONES = {"rutas", "ingesta", "calidad", "preparacion", "periodos", "poblacion", "modelo", "referencia", "columnas", "evaluacion", "seguimiento"}
COLUMNAS_SERIE = ("fecha", "viajeros", "registros", "conjunto")
COLUMNAS_COMPARACION = ("fecha", "observado", "sarima", "fecha_referencia", "referencia", "error_sarima", "error_referencia")
FORMATO_FECHA_SERIE = "%Y-%m-%d"
ARCHIVO_BASE_MLFLOW = "mlflow.db"
CARPETA_ARTEFACTOS_MLFLOW = "artefactos"


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
    archivos_generados = (
        "ingesta", "reporte_ingesta", "validado", "reporte_validacion",
        "serie_mensual", "ajuste", "evaluacion", "reporte_preparacion",
        "modelo_ajustado", "reporte_ajuste", "comparacion", "reporte_evaluacion", "candidato", "reporte_exportacion",
    )
    for clave in ("entrenamiento", "prueba", "procesados", "publicaciones", "mlflow", *archivos_generados):
        if clave not in rutas:
            raise ValueError(f"Falta la ruta {clave}.")
        rutas[clave] = resolver_ruta(raiz, rutas[clave])

    entradas = [rutas["entrenamiento"], rutas["prueba"]]
    if entradas[0] == entradas[1]:
        raise ValueError("Entrenamiento y prueba deben ser archivos diferentes.")
    if any(entrada.is_relative_to(rutas["procesados"]) for entrada in entradas):
        raise ValueError("Los insumos no pueden estar en la carpeta de resultados.")
    for clave in ("publicaciones", "mlflow", *archivos_generados):
        if not rutas[clave].is_relative_to(rutas["procesados"]):
            raise ValueError(f"La ruta {clave} debe estar dentro de procesados.")
    salidas = [rutas[clave] for clave in archivos_generados]
    if len(set(salidas)) != len(salidas) or any(salida == rutas["procesados"] for salida in salidas):
        raise ValueError("Las salidas deben ser archivos diferentes dentro de procesados.")
    if any(a != b and (a.is_relative_to(b) or b.is_relative_to(a)) for a in salidas for b in salidas):
        raise ValueError("Un archivo de salida no puede ser carpeta de otro archivo.")
    for directorio in (rutas["publicaciones"], rutas["mlflow"]):
        if any(s.is_relative_to(directorio) or directorio.is_relative_to(s) for s in salidas):
            raise ValueError("Las salidas de etapas deben estar separadas de MLflow y publicaciones.")

    seguimiento = configuracion["seguimiento"]
    if seguimiento.get("almacen") != "sqlite":
        raise ValueError("El seguimiento local utiliza SQLite.")
    experimento = seguimiento.get("experimento")
    if not isinstance(experimento, str) or not experimento.strip():
        raise ValueError("seguimiento.experimento debe ser un nombre no vacio.")

    ingesta = configuracion["ingesta"]
    for clave in ("codificacion", "separador", "columna_origen"):
        if not isinstance(ingesta.get(clave), str) or not ingesta[clave].strip():
            raise ValueError(f"ingesta.{clave} debe ser un texto no vacio.")
    if len(ingesta["separador"]) != 1:
        raise ValueError("El separador CSV debe tener un solo caracter.")
    calidad = configuracion["calidad"]
    if type(calidad.get("limite_ejemplos")) is not int or calidad["limite_ejemplos"] < 1:
        raise ValueError("calidad.limite_ejemplos debe ser un entero positivo.")
    if not isinstance(calidad.get("marcadores_ausencia"), list) or not all(
        isinstance(valor, str) for valor in calidad["marcadores_ausencia"]
    ):
        raise ValueError("Los marcadores de ausencia deben ser una lista de textos.")
    if not isinstance(calidad.get("formato_fecha"), str) or not calidad["formato_fecha"]:
        raise ValueError("calidad.formato_fecha debe indicar el formato de las fechas.")
    if not isinstance(calidad.get("tipos_fuente"), list) or not calidad["tipos_fuente"] or not all(
        isinstance(valor, str) and valor for valor in calidad["tipos_fuente"]
    ):
        raise ValueError("calidad.tipos_fuente debe indicar las categorias del contrato de entrada.")
    requeridas = columnas_requeridas(configuracion)
    clave_registro = configuracion["columnas"]["clave_registro"]
    clave_parcial = calidad.get("clave_revision_parcial")
    if len(set(clave_registro)) != len(clave_registro):
        raise ValueError("La clave de registro no puede repetir columnas.")
    if not isinstance(clave_parcial, list) or not clave_parcial or not set(clave_parcial) < set(clave_registro):
        raise ValueError("La clave parcial debe ser un subconjunto propio de la clave de registro.")
    if ingesta["columna_origen"] in requeridas:
        raise ValueError("La columna de origen debe ser diferente de las columnas de la fuente.")
    for clave in ("tipos_incluidos", "paises_excluidos"):
        valores = configuracion["poblacion"].get(clave)
        if not isinstance(valores, list) or not valores or not all(isinstance(v, str) and v for v in valores):
            raise ValueError(f"poblacion.{clave} debe ser una lista no vacia de textos.")
    for clave in ("destino", "unidad"):
        if not isinstance(configuracion["poblacion"].get(clave), str) or not configuracion["poblacion"][clave]:
            raise ValueError(f"poblacion.{clave} debe ser un texto no vacio.")
    for clave in ("tolerancia_relativa_suma", "tolerancia_absoluta_suma"):
        valor = configuracion["preparacion"].get(clave)
        if type(valor) not in (int, float) or not math.isfinite(valor) or valor < 0:
            raise ValueError(f"preparacion.{clave} debe ser un numero finito no negativo.")

    validar_periodos(configuracion["periodos"])
    modelo = configuracion["modelo"]
    if modelo.get("nombre") != "sarima" or modelo.get("transformacion") != "log":
        raise ValueError("Esta implementacion utiliza SARIMA con transformacion logaritmica.")
    if modelo.get("tendencia") not in ("n", "c", "t", "ct"):
        raise ValueError("La tendencia debe ser n, c, t o ct.")
    if modelo.get("metodo_optimizacion") != "lbfgs":
        raise ValueError("El metodo de optimizacion implementado es lbfgs.")
    if type(modelo.get("iteraciones_maximas")) is not int or modelo["iteraciones_maximas"] < 1:
        raise ValueError("Las iteraciones maximas deben ser un entero positivo.")
    for clave in ("exigir_estacionariedad", "exigir_invertibilidad"):
        if type(modelo.get(clave)) is not bool:
            raise ValueError(f"modelo.{clave} debe ser true o false.")
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
    if configuracion["evaluacion"].get("regla") != "mae_y_rmse_estrictamente_menores":
        raise ValueError("La regla implementada exige MAE y RMSE estrictamente menores que la referencia.")
    if configuracion["referencia"].get("nombre") != "mismo_mes_anio_anterior" or rezago != 12:
        raise ValueError("La referencia implementada utiliza el mismo mes del anio anterior, con rezago 12.")
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
