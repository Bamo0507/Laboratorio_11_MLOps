"""
Etapa 3 del pipeline: PREPARACION DE LA SERIE MENSUAL
------------------------------------------------------------
Una sola responsabilidad: construir la serie objetivo y sus particiones temporales.

  Lee : validado y reporte_validacion, segun configuracion.toml
  Hace: - exige controles aptos y huellas vigentes de datos y configuracion
        - conserva los tipos de visitantes configurados y excluye residentes
        - suma por mes, sin redondear ni completar ausencias con cero
        - separa ajuste y evaluacion mediante los periodos configurados
  Escribe: serie_mensual, ajuste, evaluacion y reporte_preparacion

Ejecutar: python pipeline/src/03_preparacion.py
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import RUTA_CONFIGURACION, cargar_configuracion
from utils import afirmar, banner, cargar, cargar_json, guardar, guardar_json, huella_archivo
from validacion import CONTROLES, meses_necesarios


def exigir_validacion(configuracion: dict[str, Any], ruta_configuracion: Path, sha_validado: str) -> dict[str, Any]:
    rutas = configuracion["rutas"]
    calidad = cargar_json(rutas["reporte_validacion"])
    afirmar(calidad.get("apto_para_preparacion") is True, "el reporte de calidad permite preparar la serie")
    controles = calidad.get("controles", [])
    afirmar(
        len(controles) == len(CONTROLES)
        and {c.get("codigo") for c in controles} == {codigo for codigo, _ in CONTROLES}
        and all(c.get("estado") in ("ok", "advertencia") for c in controles),
        "los seis controles fueron evaluados sin errores criticos",
    )
    afirmar(calidad.get("sha256_validado") == sha_validado, "el CSV validado coincide con su reporte")
    afirmar(
        calidad.get("sha256_configuracion") == huella_archivo(ruta_configuracion),
        "la configuracion coincide con la utilizada al validar; si cambia, se debe repetir la validacion",
    )
    afirmar(calidad.get("sha256_ingesta") == huella_archivo(rutas["ingesta"]), "la ingesta no cambio despues de validarse")
    raiz = ruta_configuracion.resolve().parent
    fuentes = {f["archivo"]: f for f in calidad.get("fuentes", [])}
    esperadas = {rutas[k].relative_to(raiz).as_posix() for k in ("entrenamiento", "prueba")}
    afirmar(set(fuentes) == esperadas, "el reporte identifica las fuentes configuradas")
    for clave in ("entrenamiento", "prueba"):
        nombre = rutas[clave].relative_to(raiz).as_posix()
        afirmar(fuentes[nombre].get("sha256") == huella_archivo(rutas[clave]), f"{clave}: la fuente original no cambio")
    return calidad


def preparar(datos: pd.DataFrame, configuracion: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    col, poblacion = configuracion["columnas"], configuracion["poblacion"]
    fechas = pd.to_datetime(datos[col["fecha"]], format=configuracion["calidad"]["formato_fecha"], errors="raise")
    tipos = datos[col["tipo"]].isin(poblacion["tipos_incluidos"])
    residentes = datos[col["pais"]].isin(poblacion["paises_excluidos"])
    seleccion = tipos & ~residentes
    afirmar(bool(seleccion.any()), "hay registros de la poblacion objetivo")
    valores = pd.to_numeric(datos.loc[seleccion, col["valor"]], errors="raise")
    afirmar(bool(np.isfinite(valores.to_numpy(dtype=float)).all() and valores.ge(0).all()), "los conteos seleccionados son finitos y no negativos")
    seleccionados = pd.DataFrame({"fecha": fechas[seleccion], "viajeros": valores})
    totales = seleccionados.groupby("fecha")["viajeros"].sum(min_count=1)
    registros = seleccionados.groupby("fecha").size()
    afirmar(bool(np.isfinite(totales.to_numpy(dtype=float)).all()), "todos los meses con registros tienen totales finitos")

    # Cero registros informa ausencia de cobertura; el total queda NaN, nunca cero.
    calendario = pd.date_range(fechas.min(), fechas.max(), freq="MS")
    serie = pd.DataFrame({
        "fecha": calendario,
        "viajeros": totales.reindex(calendario).to_numpy(),
        "registros": registros.reindex(calendario, fill_value=0).to_numpy(),
    })
    necesarios = meses_necesarios(configuracion)
    periodos_fila = serie["fecha"].dt.to_period("M")
    serie["conjunto"] = "historico"
    serie.loc[periodos_fila.isin(necesarios["ajuste"]), "conjunto"] = "ajuste"
    serie.loc[periodos_fila.isin(necesarios["evaluacion"]), "conjunto"] = "evaluacion"
    for nombre, meses in necesarios.items():
        tramo = serie.loc[periodos_fila.isin(meses), "viajeros"]
        afirmar(len(tramo) == len(meses) and tramo.notna().all(), f"{nombre}: todos los meses necesarios tienen un total observado")
        afirmar(bool(np.isfinite(tramo.to_numpy(dtype=float)).all()), f"{nombre}: los totales son finitos")
        if configuracion["modelo"]["transformacion"] == "log":
            afirmar(bool(tramo.gt(0).all()), f"{nombre}: los totales permiten aplicar el logaritmo")
    afirmar(serie["fecha"].is_unique, "la serie tiene una sola fila por mes")
    suma_entrada = float(valores.sum())
    suma_salida = float(serie["viajeros"].sum(min_count=1))
    afirmar(bool(np.isfinite([suma_entrada, suma_salida]).all()), "los totales globales son finitos")
    opciones = configuracion["preparacion"]
    afirmar(bool(np.isclose(
        suma_entrada, suma_salida,
        rtol=opciones["tolerancia_relativa_suma"],
        atol=opciones["tolerancia_absoluta_suma"],
    )), "la agregacion conserva el total de llegadas seleccionadas")
    resumen = {
        "filas_entrada": len(datos),
        "filas_seleccionadas": int(seleccion.sum()),
        "filas_residentes_excluidas": int((tipos & residentes).sum()),
        "filas_otros_tipos_excluidas": int((~tipos).sum()),
        "total_llegadas_seleccionadas": suma_entrada,
        "meses_serie": len(serie),
        "meses_sin_cobertura": serie.loc[serie["viajeros"].isna(), "fecha"].dt.strftime("%Y-%m").tolist(),
        "periodos": configuracion["periodos"],
        "poblacion": poblacion,
        "referencia": configuracion["referencia"],
        "tolerancias_suma": opciones,
        "politica": "Sin imputacion, redondeo, deduplicacion ni uso de evaluacion para transformar el ajuste.",
    }
    serie["fecha"] = serie["fecha"].dt.strftime("%Y-%m-%d")
    salidas = {
        "serie_mensual": serie,
        "ajuste": serie.loc[serie["conjunto"].eq("ajuste")].reset_index(drop=True),
        "evaluacion": serie.loc[serie["conjunto"].eq("evaluacion")].reset_index(drop=True),
    }
    resumen["meses_ajuste"] = len(salidas["ajuste"])
    resumen["meses_evaluacion"] = len(salidas["evaluacion"])
    return salidas, resumen


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION) -> dict[str, Any]:
    configuracion = cargar_configuracion(ruta_configuracion)
    rutas = configuracion["rutas"]
    raiz = Path(ruta_configuracion).resolve().parent
    banner("Etapa 3: preparacion mensual")
    try:
        datos, metadatos = cargar(rutas["validado"], "utf-8", configuracion["ingesta"]["separador"])
        exigir_validacion(configuracion, ruta_configuracion, metadatos["sha256"])
        salidas, resumen = preparar(datos, configuracion)
    except (OSError, ValueError, TypeError, KeyError) as error:
        guardar_json({
            "etapa": "03_preparacion", "estado": "rechazado", "publicacion_autorizada": False,
            "error": str(error), "sha256_configuracion": huella_archivo(ruta_configuracion),
        }, rutas["reporte_preparacion"])
        raise

    archivos = {}
    for nombre, tabla in salidas.items():
        guardar(tabla, rutas[nombre], separador=configuracion["ingesta"]["separador"])
        archivos[nombre] = {"ruta": rutas[nombre].relative_to(raiz).as_posix(), "sha256": huella_archivo(rutas[nombre])}
    resultado = {
        "etapa": "03_preparacion", "estado": "completada", "publicacion_autorizada": False,
        "sha256_configuracion": huella_archivo(ruta_configuracion),
        "sha256_validado": metadatos["sha256"],
        "sha256_reporte_validacion": huella_archivo(rutas["reporte_validacion"]),
        "archivos": archivos, **resumen,
    }
    guardar_json(resultado, rutas["reporte_preparacion"])
    print(f"[ok] Serie preparada: {resumen['meses_ajuste']} meses de ajuste y {resumen['meses_evaluacion']} de evaluacion.")
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description="Preparar la serie mensual sin residentes.")
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"[FALLO] Preparacion detenida: {error}\n")


if __name__ == "__main__":
    main()
