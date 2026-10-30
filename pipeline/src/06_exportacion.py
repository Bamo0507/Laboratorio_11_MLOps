"""
Etapa 6 del pipeline: EXPORTACION DE ESTIMACIONES CANDIDATAS
------------------------------------------------------------
Una sola responsabilidad: empaquetar las estimaciones evaluadas para revision.

  Lee : comparacion, reporte_evaluacion y certificados anteriores
  Hace: - verifica vigencia, fechas, valores y metricas
        - conserva la decision de desempeno incluso cuando es desfavorable
        - construye un JSON independiente del tablero
  Escribe: candidato y reporte_exportacion, segun configuracion.toml

Ejecutar: python pipeline/src/06_exportacion.py
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from uuid import UUID, uuid4
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import COLUMNAS_COMPARACION, FORMATO_FECHA_SERIE, RUTA_CONFIGURACION, cargar_configuracion
from utils import afirmar, banner, cargar, cargar_json, guardar_json, huella_archivo

evaluacion = import_module("05_evaluacion")


def verificar_entradas(configuracion: dict[str, Any], ruta_configuracion: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    rutas = configuracion["rutas"]
    afirmar(configuracion["evaluacion"]["observaciones_comparables"] is True, "las observaciones siguen declaradas comparables")
    raiz = ruta_configuracion.resolve().parent
    reporte = cargar_json(rutas["reporte_evaluacion"])
    afirmar(reporte.get("estado") == "completada", "la evaluacion termino correctamente")
    afirmar(reporte["sha256_configuracion"] == huella_archivo(ruta_configuracion), "la configuracion coincide con la evaluacion")
    afirmar(reporte["regla"] == configuracion["evaluacion"], "se conserva la regla de desempeno previa")
    for nombre in ("modelo_ajustado", "reporte_ajuste", "reporte_preparacion", "ajuste", "evaluacion", "serie_mensual"):
        afirmar(reporte["entradas"][nombre] == huella_archivo(rutas[nombre]), f"{nombre}: coincide con la evaluacion")
    _, meta_ajuste = cargar(rutas["ajuste"], "utf-8", configuracion["ingesta"]["separador"])
    evaluacion.ajuste.exigir_preparacion(configuracion, ruta_configuracion, meta_ajuste["sha256"])
    datos, metadatos = cargar(rutas["comparacion"], "utf-8", configuracion["ingesta"]["separador"])
    afirmar(reporte["comparacion"]["sha256"] == metadatos["sha256"]
            and reporte["comparacion"]["ruta"] == rutas["comparacion"].relative_to(raiz).as_posix(),
            "la comparacion coincide con el archivo certificado")
    afirmar(list(datos.columns) == list(COLUMNAS_COMPARACION), "la comparacion cumple el contrato de columnas")
    periodos = configuracion["periodos"]
    fechas = pd.date_range(f"{periodos['inicio_evaluacion']}-01", f"{periodos['fin_evaluacion']}-01", freq="MS")
    fechas_csv = pd.to_datetime(datos["fecha"], format=FORMATO_FECHA_SERIE, errors="raise")
    afirmar(pd.DatetimeIndex(fechas_csv).equals(fechas), "las estimaciones contienen exactamente los meses evaluados")
    referencia = fechas - pd.DateOffset(months=configuracion["referencia"]["rezago_meses"])
    afirmar(pd.DatetimeIndex(pd.to_datetime(datos["fecha_referencia"], format=FORMATO_FECHA_SERIE, errors="raise")).equals(referencia),
            "cada referencia corresponde al mismo mes del anio anterior")
    for nombre in COLUMNAS_COMPARACION:
        if nombre not in ("fecha", "fecha_referencia"):
            datos[nombre] = pd.to_numeric(datos[nombre], errors="raise")
            valores = datos[nombre].to_numpy(dtype=float)
            afirmar(bool(np.isfinite(valores).all()), f"{nombre}: valores finitos")
            if nombre in ("observado", "sarima", "referencia"):
                afirmar(bool((valores > 0).all()), f"{nombre}: llegadas positivas")
    for nombre in ("sarima", "referencia"):
        afirmar(bool(np.allclose(datos[f"error_{nombre}"], datos[nombre] - datos["observado"], rtol=1e-12, atol=1e-8)),
                f"{nombre}: el error conserva su definicion")
        calculadas = evaluacion.metricas(datos["observado"].to_numpy(), datos[nombre].to_numpy())
        for metrica, valor in calculadas.items():
            registrado = reporte["metricas"][nombre][metrica]
            afirmar(type(registrado) in (int, float) and bool(np.isfinite(registrado))
                    and bool(np.isclose(valor, registrado, rtol=1e-12, atol=1e-8)), f"{nombre}: {metrica} coincide con la comparacion")
    decision = evaluacion.supera_regla(reporte["metricas"]["sarima"], reporte["metricas"]["referencia"])
    afirmar(type(reporte.get("supera_regla_desempeno")) is bool and reporte["supera_regla_desempeno"] == decision,
            "la decision registrada coincide con los errores y la regla")
    afirmar(reporte.get("publicacion_autorizada") is False, "la evaluacion no autoriza una publicacion")
    afirmar(reporte["periodo"] == {"inicio": periodos["inicio_evaluacion"], "fin": periodos["fin_evaluacion"], "meses": len(fechas)},
            "el periodo declarado coincide con las estimaciones")
    afirmar(reporte["unidad"] == configuracion["poblacion"]["unidad"], "se conserva la unidad de las metricas")
    return reporte, datos


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION, id_ejecucion_mlflow: str | None = None) -> dict[str, Any]:
    configuracion = cargar_configuracion(ruta_configuracion)
    rutas = configuracion["rutas"]
    raiz = Path(ruta_configuracion).resolve().parent
    if id_ejecucion_mlflow is not None:
        UUID(id_ejecucion_mlflow)
    banner("Etapa 6: exportacion candidata")
    try:
        evaluada, datos = verificar_entradas(configuracion, Path(ruta_configuracion))
        supera = evaluada["supera_regla_desempeno"]
        entradas = {nombre: huella_archivo(rutas[nombre]) for nombre in ("comparacion", "reporte_evaluacion")}
        candidato = {
            "version_esquema": 1, "tipo": "estimaciones_evaluadas", "publicacion_autorizada": False,
            "supera_regla_desempeno": supera,
            "estado_desempeno": "supera_regla" if supera else "no_supera_regla",
            "motivo": "Pendiente del proceso de publicacion." if supera else "SARIMA no mejora simultaneamente MAE y RMSE frente a la referencia.",
            "poblacion": configuracion["poblacion"], "periodo": evaluada["periodo"],
            "modelo": configuracion["modelo"], "referencia": configuracion["referencia"],
            "regla": evaluada["regla"], "metricas": evaluada["metricas"],
            "metodo": evaluada["metodo"], "transformacion_inversa": evaluada["transformacion_inversa"],
            "limitacion": evaluada["limitacion"],
            "protocolo_temporal": evaluada["protocolo_temporal"],
            "comparabilidad": evaluada["comparabilidad"],
            "diagnostico": evaluada["diagnostico"],
            "estimaciones": datos.to_dict(orient="records"),
            "trazabilidad": {"sha256_configuracion": huella_archivo(ruta_configuracion), "entradas": entradas},
        }
        guardar_json(candidato, rutas["candidato"])
        recuperado = cargar_json(rutas["candidato"])
        afirmar(recuperado == candidato, "el candidato exportado conserva exactamente su contenido")
        reporte = {
            "etapa": "06_exportacion", "estado": "completada", "publicacion_autorizada": False,
            "id_ejecucion_local": uuid4().hex, "id_ejecucion_mlflow": id_ejecucion_mlflow, "fecha_generacion": datetime.now(timezone.utc).isoformat(),
            "supera_regla_desempeno": supera, "estimaciones": len(datos),
            "sha256_configuracion": huella_archivo(ruta_configuracion), "entradas": entradas,
            "candidato": {"ruta": rutas["candidato"].relative_to(raiz).as_posix(), "sha256": huella_archivo(rutas["candidato"])},
            "codigo": evaluacion.ajuste.version_codigo(),
        }
        guardar_json(reporte, rutas["reporte_exportacion"])
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, FloatingPointError) as error:
        guardar_json({"etapa": "06_exportacion", "estado": "rechazado", "publicacion_autorizada": False,
                      "supera_regla_desempeno": False, "error": str(error)}, rutas["reporte_exportacion"])
        raise
    print(f"[ok] Candidato exportado con {len(datos)} estimaciones. Supera desempeno: {supera}. Publicacion pendiente.")
    return reporte


def main() -> None:
    parser = argparse.ArgumentParser(description="Exportar estimaciones evaluadas sin publicarlas.")
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    parser.add_argument("--id-ejecucion-mlflow", default=None)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config, argumentos.id_ejecucion_mlflow)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, FloatingPointError) as error:
        parser.exit(1, f"[FALLO] Exportacion detenida: {error}\n")


if __name__ == "__main__":
    main()
