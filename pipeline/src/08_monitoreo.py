"""
Etapa 8 del pipeline: MONITOREO
------------------------------------------------------------
Una sola responsabilidad: emitir alertas para revision, sin bloquear ni publicar.

  Lee : fuentes, reportes de ingesta, validacion y evaluacion, candidato y version vigente
  Hace: - actualizacion: fuentes y resultados llegan al ultimo periodo configurado
        - calidad: cambios en filas, faltantes, duplicados y cobertura frente al monitoreo anterior
        - resultados: estimaciones negativas, no finitas o con variacion interanual sobre el umbral
  Escribe: reporte_monitoreo

Ejecutar: python pipeline/src/08_monitoreo.py
"""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config import RUTA_CONFIGURACION, cargar_configuracion
from publicacion import consultar_vigente
from utils import banner, cargar_json, guardar_json, huella_archivo

INDICADORES_CALIDAD = ("faltantes", "duplicados_completos", "coincidencias_parciales", "meses_sin_cobertura")


def verificacion(codigo: str, alertas: list[str], **detalles: Any) -> dict[str, Any]:
    for alerta in alertas:
        print(f"[ALERTA] {codigo}: {alerta}", flush=True)
    if not alertas:
        print(f"[ok] {codigo}: sin alertas", flush=True)
    return {"codigo": codigo, "estado": "alerta" if alertas else "ok", "alertas": alertas, "detalles": detalles}


def verificar_actualizacion(configuracion: dict[str, Any], candidato: dict[str, Any], vigente: dict[str, Any] | None) -> dict[str, Any]:
    rutas, col = configuracion["rutas"], configuracion["columnas"]
    esperado = configuracion["periodos"]["fin_evaluacion"]
    meses = []
    for nombre in ("entrenamiento", "prueba"):
        fechas = pd.read_csv(rutas[nombre], usecols=[col["fecha"]], dtype=str, keep_default_na=False,
                             encoding=configuracion["ingesta"]["codificacion"], sep=configuracion["ingesta"]["separador"])[col["fecha"]]
        meses.append(pd.to_datetime(fechas, format=configuracion["calidad"]["formato_fecha"], errors="coerce").max())
    ultimo_fuente = max(meses).strftime("%Y-%m")
    procesadas = {f["sha256"] for f in cargar_json(rutas["reporte_ingesta"])["fuentes"]}
    actuales = {huella_archivo(rutas[nombre]) for nombre in ("entrenamiento", "prueba")}
    alertas = []
    if ultimo_fuente < esperado:
        alertas.append(f"Las fuentes llegan hasta {ultimo_fuente}; el ultimo periodo esperado es {esperado}.")
    elif ultimo_fuente > esperado:
        alertas.append(f"Las fuentes tienen meses hasta {ultimo_fuente} que la configuracion todavia no utiliza.")
    if actuales != procesadas:
        alertas.append("Las fuentes cambiaron despues de la ultima ingesta; los resultados no corresponden a los datos actuales.")
    if candidato["periodo"]["fin"] != esperado:
        alertas.append(f"El candidato termina en {candidato['periodo']['fin']}; se esperaba {esperado}.")
    if vigente is None:
        alertas.append("No hay una version aprobada; el tablero informa que las estimaciones no estan disponibles.")
    elif vigente["periodo"]["fin"] != esperado:
        alertas.append(f"La version vigente termina en {vigente['periodo']['fin']}; se esperaba {esperado}.")
    return verificacion("actualizacion", alertas, periodo_esperado=esperado, ultimo_mes_fuentes=ultimo_fuente,
                        fuentes_procesadas=actuales == procesadas, fin_candidato=candidato["periodo"]["fin"],
                        version_vigente=vigente["version"] if vigente else None,
                        fin_vigente=vigente["periodo"]["fin"] if vigente else None)


def resumen_calidad(reporte: dict[str, Any]) -> dict[str, int] | None:
    """Indicadores comparables entre ejecuciones; None si la validacion no fue apta."""
    if reporte.get("estado") not in ("apto", "apto_con_advertencias"):
        return None
    detalles = {control["codigo"]: control["detalles"] for control in reporte["controles"]}
    faltantes, unicidad, cobertura = detalles["faltantes"], detalles["unicidad"], detalles["fechas_cobertura"]
    return {
        "filas": reporte["filas_entrada"],
        "faltantes": sum(faltantes["faltantes_criticos"].values()) + sum(faltantes["faltantes_permitidos"].values()),
        "duplicados_completos": unicidad["duplicados_completos"],
        "coincidencias_parciales": unicidad["coincidencias_parciales"],
        "meses_sin_cobertura": len(cobertura["meses_sin_cobertura_fuera_periodos"]) + sum(len(m) for m in cobertura["meses_sin_cobertura"].values()),
    }


def verificar_calidad(actual: dict[str, int] | None, anterior: dict[str, int] | None) -> dict[str, Any]:
    """Una base historica no deberia perder filas ni ganar faltantes, duplicados o meses sin cobertura."""
    if actual is None:
        return verificacion("calidad", ["La ultima validacion no fue apta; no hay indicadores para comparar."], actual=None, anterior=anterior)
    alertas = []
    if anterior is not None:
        if actual["filas"] < anterior["filas"]:
            alertas.append(f"Las fuentes pasaron de {anterior['filas']} a {actual['filas']} filas.")
        alertas.extend(f"{clave} aumento de {anterior[clave]} a {actual[clave]}." for clave in INDICADORES_CALIDAD if actual[clave] > anterior[clave])
    return verificacion("calidad", alertas, actual=actual, anterior=anterior,
                        referencia="Monitoreo anterior" if anterior else "Primera ejecucion monitoreada; queda como referencia.")


def verificar_resultados(estimaciones: list[dict[str, Any]], umbral: float) -> dict[str, Any]:
    """Una variacion elevada pide revision; por si sola no demuestra perdida de precision."""
    alertas, variaciones = [], {}
    for fila in estimaciones:
        mes, valor, referencia = fila["fecha"][:7], fila["sarima"], fila["referencia"]
        if not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < 0:
            alertas.append(f"{mes}: estimacion negativa o no finita ({valor}).")
            continue
        variaciones[mes] = valor / referencia - 1
        if abs(variaciones[mes]) > umbral:
            alertas.append(f"{mes}: la estimacion varia {variaciones[mes]:+.1%} frente al mismo mes del anio anterior (umbral {umbral:.0%}).")
    return verificacion("resultados", alertas, umbral_variacion_interanual=umbral, variaciones_interanuales=variaciones)


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION) -> dict[str, Any]:
    configuracion = cargar_configuracion(ruta_configuracion)
    rutas = configuracion["rutas"]
    banner("Etapa 8: monitoreo")
    previo = cargar_json(rutas["reporte_monitoreo"]) if rutas["reporte_monitoreo"].exists() else {}
    anterior = previo.get("resumen_calidad")
    candidato = cargar_json(rutas["candidato"])
    vigente = consultar_vigente(rutas["publicaciones"])
    actual = resumen_calidad(cargar_json(rutas["reporte_validacion"]))
    evaluacion = cargar_json(rutas["reporte_evaluacion"])
    # El error predictivo solo se informa cuando hubo observaciones comparables para calcularlo.
    comparable = evaluacion.get("estado") == "completada" and evaluacion["comparabilidad"]["observaciones_comparables"] is True
    verificaciones = [
        verificar_actualizacion(configuracion, candidato, vigente),
        verificar_calidad(actual, anterior),
        verificar_resultados(candidato["estimaciones"], configuracion["monitoreo"]["variacion_interanual_maxima"]),
    ]
    reporte = {
        "etapa": "08_monitoreo", "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "estado": "con_alertas" if any(v["alertas"] for v in verificaciones) else "sin_alertas",
        "verificaciones": verificaciones,
        "resumen_calidad": actual or anterior,
        "error_predictivo": {"periodo": evaluacion["periodo"], "metricas": evaluacion["metricas"]} if comparable else None,
        "nota": "Las alertas piden revision; no bloquean ni revierten la publicacion.",
    }
    guardar_json(reporte, rutas["reporte_monitoreo"])
    print(f"[ok] Monitoreo: {reporte['estado']}.")
    return reporte


def main() -> None:
    parser = argparse.ArgumentParser(description="Comprobar actualizacion, calidad y resultados sin modificar publicaciones.")
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"[FALLO] Monitoreo detenido: {error}\n")


if __name__ == "__main__":
    main()
