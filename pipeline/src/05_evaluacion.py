"""
Etapa 5 del pipeline: EVALUACION CONTRA REFERENCIA
------------------------------------------------------------
Una sola responsabilidad: medir el error fuera del ajuste con una regla previa.

  Lee : modelo_ajustado, ajuste, evaluacion, serie_mensual y reportes previos
  Hace: - verifica la vigencia de los insumos
        - pronostica todo el horizonte sin incorporar observaciones de prueba
        - compara SARIMA y el mismo mes del anio anterior con MAE y RMSE
  Escribe: comparacion y reporte_evaluacion, segun configuracion.toml

Ejecutar: python pipeline/src/05_evaluacion.py
"""

from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAXResults

from config import COLUMNAS_SERIE, FORMATO_FECHA_SERIE, RUTA_CONFIGURACION, cargar_configuracion
from utils import afirmar, banner, cargar, cargar_json, guardar, guardar_json, huella_archivo

ajuste = import_module("04_ajuste")


def metricas(observado: np.ndarray, predicho: np.ndarray) -> dict[str, float]:
    observado, predicho = np.asarray(observado, dtype=float), np.asarray(predicho, dtype=float)
    afirmar(observado.ndim == 1 and observado.size > 0 and observado.shape == predicho.shape,
            "las metricas comparan vectores no vacios del mismo tamano")
    afirmar(bool(np.isfinite(observado).all() and np.isfinite(predicho).all()), "las metricas reciben valores finitos")
    with np.errstate(over="raise", invalid="raise"):
        error = predicho - observado
        resultado = {"mae": float(np.mean(np.abs(error))), "rmse": float(np.sqrt(np.mean(error ** 2)))}
    afirmar(bool(np.isfinite(list(resultado.values())).all()), "los errores calculados son finitos")
    return resultado


def supera_regla(sarima: dict[str, float], referencia: dict[str, float]) -> bool:
    return all(sarima[metrica] < referencia[metrica] for metrica in ("mae", "rmse"))


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION) -> dict[str, Any]:
    configuracion = cargar_configuracion(ruta_configuracion)
    rutas = configuracion["rutas"]
    raiz = Path(ruta_configuracion).resolve().parent
    banner("Etapa 5: evaluacion contra referencia")
    try:
        datos_ajuste, meta_ajuste = cargar(rutas["ajuste"], "utf-8", configuracion["ingesta"]["separador"])
        preparacion = ajuste.exigir_preparacion(configuracion, ruta_configuracion, meta_ajuste["sha256"])
        reporte_ajuste = cargar_json(rutas["reporte_ajuste"])
        afirmar(reporte_ajuste.get("estado") == "completada" and reporte_ajuste["convergencia"]["convergio"] is True,
                "el ajuste termino y convergio")
        afirmar(reporte_ajuste["sha256_configuracion"] == huella_archivo(ruta_configuracion), "la configuracion coincide con el ajuste")
        afirmar(reporte_ajuste["sha256_ajuste"] == meta_ajuste["sha256"], "los datos de entrenamiento coinciden con el ajuste")
        afirmar(reporte_ajuste["sha256_reporte_preparacion"] == huella_archivo(rutas["reporte_preparacion"]), "la preparacion coincide con el ajuste")
        afirmar(reporte_ajuste["modelo"]["sha256"] == huella_archivo(rutas["modelo_ajustado"]), "el modelo conserva la huella registrada")
        tablas = {}
        for nombre in ("evaluacion", "serie_mensual"):
            datos, meta = cargar(rutas[nombre], "utf-8", configuracion["ingesta"]["separador"])
            certificado = preparacion["archivos"][nombre]
            afirmar(certificado["sha256"] == meta["sha256"] and certificado["ruta"] == rutas[nombre].relative_to(raiz).as_posix(),
                    f"{nombre}: el archivo coincide con la preparacion")
            afirmar(list(datos.columns) == list(COLUMNAS_SERIE), f"{nombre}: columnas de la serie preparada")
            datos["fecha"] = pd.to_datetime(datos["fecha"], format=FORMATO_FECHA_SERIE, errors="raise")
            afirmar(datos["fecha"].is_unique and datos["fecha"].is_monotonic_increasing, f"{nombre}: fechas unicas y ordenadas")
            tablas[nombre] = datos.set_index("fecha")
        periodos = configuracion["periodos"]
        fechas = pd.date_range(f"{periodos['inicio_evaluacion']}-01", f"{periodos['fin_evaluacion']}-01", freq="MS")
        evaluacion = tablas["evaluacion"]
        afirmar(evaluacion.index.equals(fechas) and bool(evaluacion["conjunto"].eq("evaluacion").all()), "se evaluan exactamente los meses reservados")
        serie_ajuste = ajuste.construir_serie(datos_ajuste, configuracion)
        modelo = SARIMAXResults.load(rutas["modelo_ajustado"])
        afirmar(modelo.nobs == len(serie_ajuste) and pd.DatetimeIndex(modelo.model.data.dates).equals(serie_ajuste.index), "el modelo conserva las fechas de entrenamiento")
        afirmar(np.array_equal(np.asarray(modelo.model.endog).ravel(), serie_ajuste.to_numpy()), "el modelo conserva los valores de entrenamiento")
        # Se pronostican tambien los meses intermedios si se configura una separacion temporal.
        horizonte = pd.date_range(serie_ajuste.index[-1] + pd.offsets.MonthBegin(), fechas[-1], freq="MS")
        pronostico_log = modelo.get_forecast(steps=len(horizonte)).predicted_mean
        afirmar(pd.DatetimeIndex(pronostico_log.index).equals(horizonte), "el pronostico conserva la frecuencia mensual")
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            predicciones = np.exp(pronostico_log.reindex(fechas).to_numpy(dtype=float))
        fechas_referencia = fechas - pd.DateOffset(months=configuracion["referencia"]["rezago_meses"])
        afirmar(bool((fechas_referencia <= serie_ajuste.index[-1]).all()), "la referencia solo utiliza meses conocidos al terminar el ajuste")
        referencia = pd.to_numeric(tablas["serie_mensual"].reindex(fechas_referencia)["viajeros"], errors="raise").to_numpy(dtype=float)
        observado = pd.to_numeric(evaluacion["viajeros"], errors="raise").to_numpy(dtype=float)
        afirmar(bool(np.isfinite(np.concatenate([observado, referencia, predicciones])).all()
                     and (observado > 0).all() and (referencia > 0).all() and (predicciones > 0).all()), "observaciones, referencia y pronosticos son finitos y positivos")
        resultados = {"sarima": metricas(observado, predicciones), "referencia": metricas(observado, referencia)}
        aprobado = supera_regla(resultados["sarima"], resultados["referencia"])
        comparacion = pd.DataFrame({
            "fecha": fechas.strftime(FORMATO_FECHA_SERIE), "observado": observado,
            "sarima": predicciones, "fecha_referencia": fechas_referencia.strftime(FORMATO_FECHA_SERIE),
            "referencia": referencia, "error_sarima": predicciones - observado,
            "error_referencia": referencia - observado,
        })
        guardar(comparacion, rutas["comparacion"], separador=configuracion["ingesta"]["separador"])
        reporte = {
            "etapa": "05_evaluacion", "estado": "completada", "publicacion_autorizada": False,
            "supera_regla_desempeno": aprobado, "regla": configuracion["evaluacion"],
            "metricas": resultados, "unidad": configuracion["poblacion"]["unidad"],
            "periodo": {"inicio": periodos["inicio_evaluacion"], "fin": periodos["fin_evaluacion"], "meses": len(fechas)},
            "metodo": "Pronostico de origen fijo desde el fin del ajuste. Sin reentrenamiento ni incorporacion de observaciones de evaluacion.",
            "transformacion_inversa": "Exponencial directa del pronostico logaritmico, sin correccion de sesgo. Representa una mediana condicional, no la media aritmetica esperada.",
            "limitacion": "Seis meses permiten una comparacion acotada y no garantizan el desempeno futuro. No se ajusta la regla a los errores observados.",
            "sha256_configuracion": huella_archivo(ruta_configuracion),
            "entradas": {nombre: huella_archivo(rutas[nombre]) for nombre in ("modelo_ajustado", "reporte_ajuste", "reporte_preparacion", "ajuste", "evaluacion", "serie_mensual")},
            "comparacion": {"ruta": rutas["comparacion"].relative_to(raiz).as_posix(), "sha256": huella_archivo(rutas["comparacion"])},
            "codigo": ajuste.version_codigo(),
        }
        guardar_json(reporte, rutas["reporte_evaluacion"])
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, FloatingPointError) as error:
        guardar_json({"etapa": "05_evaluacion", "estado": "rechazado", "publicacion_autorizada": False,
                      "supera_regla_desempeno": False, "error": str(error)}, rutas["reporte_evaluacion"])
        raise
    print(f"[ok] Evaluacion completada. Supera la regla de desempeno: {aprobado}. Publicacion pendiente.")
    return reporte


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluar SARIMA contra el mismo mes del anio anterior.")
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, FloatingPointError) as error:
        parser.exit(1, f"[FALLO] Evaluacion detenida: {error}\n")


if __name__ == "__main__":
    main()
