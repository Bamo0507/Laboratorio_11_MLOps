"""
Etapa 4 del pipeline: AJUSTE DEL MODELO SARIMA
------------------------------------------------------------
Una sola responsabilidad: entrenar y guardar SARIMA con los meses de ajuste.

  Lee : ajuste, reporte_preparacion y certificados anteriores
  Hace: - comprueba la vigencia de datos, configuracion y calidad
        - aplica logaritmo solo a la serie de ajuste
        - estima los parametros y exige convergencia y resultados finitos
        - guarda el modelo y comprueba que pueda recuperarse
  Escribe: modelo_ajustado y reporte_ajuste, segun configuracion.toml

Ejecutar: python pipeline/src/04_ajuste.py
"""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import subprocess
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX, SARIMAXResults

from config import COLUMNAS_SERIE, FORMATO_FECHA_SERIE, RUTA_CONFIGURACION, cargar_configuracion
from utils import afirmar, banner, cargar, cargar_json, guardar_binario, guardar_json, huella_archivo
from validacion import CONTROLES


def exigir_preparacion(configuracion: dict[str, Any], ruta_configuracion: Path, sha_ajuste: str) -> dict[str, Any]:
    rutas = configuracion["rutas"]
    preparacion = cargar_json(rutas["reporte_preparacion"])
    afirmar(preparacion.get("estado") == "completada", "la preparacion termino correctamente")
    afirmar(preparacion.get("sha256_configuracion") == huella_archivo(ruta_configuracion), "la configuracion no cambio despues de preparar los datos")
    archivo = preparacion["archivos"]["ajuste"]
    afirmar(archivo["sha256"] == sha_ajuste, "el archivo de ajuste coincide con la preparacion")
    afirmar(archivo["ruta"] == rutas["ajuste"].relative_to(ruta_configuracion.resolve().parent).as_posix(), "se utiliza el archivo de ajuste declarado")
    calidad = cargar_json(rutas["reporte_validacion"])
    afirmar(calidad.get("apto_para_preparacion") is True, "el reporte de calidad sigue siendo apto")
    controles = calidad.get("controles", [])
    afirmar(
        len(controles) == len(CONTROLES)
        and {c.get("codigo") for c in controles} == {codigo for codigo, _ in CONTROLES}
        and all(c.get("estado") in ("ok", "advertencia") for c in controles),
        "los seis controles mantienen un resultado permitido",
    )
    afirmar(preparacion["sha256_reporte_validacion"] == huella_archivo(rutas["reporte_validacion"]), "el reporte de calidad no cambio despues de la preparacion")
    afirmar(preparacion["sha256_validado"] == huella_archivo(rutas["validado"]), "el archivo validado no cambio")
    afirmar(calidad["sha256_ingesta"] == huella_archivo(rutas["ingesta"]), "la ingesta no cambio")
    raiz = ruta_configuracion.resolve().parent
    fuentes = {fuente["archivo"]: fuente for fuente in calidad["fuentes"]}
    for clave in ("entrenamiento", "prueba"):
        nombre = rutas[clave].relative_to(raiz).as_posix()
        afirmar(fuentes[nombre]["sha256"] == huella_archivo(rutas[clave]), f"{clave}: la fuente original no cambio")
    return preparacion


def construir_serie(datos: pd.DataFrame, configuracion: dict[str, Any]) -> pd.Series:
    afirmar(list(datos.columns) == list(COLUMNAS_SERIE), "el archivo cumple el contrato de la serie preparada")
    fechas = pd.to_datetime(datos["fecha"], format=FORMATO_FECHA_SERIE, errors="raise")
    periodos = configuracion["periodos"]
    esperadas = pd.date_range(f"{periodos['inicio_ajuste']}-01", f"{periodos['fin_ajuste']}-01", freq="MS")
    afirmar(pd.DatetimeIndex(fechas).equals(esperadas), "los meses coinciden exactamente con el ajuste configurado, en orden y sin huecos")
    afirmar(bool(datos["conjunto"].eq("ajuste").all()), "solo se utilizan filas marcadas como ajuste")
    valores = pd.to_numeric(datos["viajeros"], errors="raise").to_numpy(dtype=float)
    afirmar(bool(np.isfinite(valores).all() and (valores > 0).all()), "las llegadas de ajuste son finitas y positivas")
    opciones = configuracion["modelo"]
    diferencias = opciones["orden"][1] + opciones["orden_estacional"][1] * opciones["orden_estacional"][-1]
    afirmar(len(valores) > diferencias, "hay observaciones despues de las diferencias configuradas")
    return pd.Series(np.log(valores), index=esperadas, name="log_llegadas")


def version_codigo() -> dict[str, Any]:
    raiz_codigo = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.check_output(["git", "-C", str(raiz_codigo), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        cambios = subprocess.check_output(["git", "-C", str(raiz_codigo), "status", "--porcelain", "--", "pipeline/src", "pipeline/configuracion.toml", "pipeline/requirements.txt"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit, cambios = None, None
    return {
        "commit": commit,
        "cambios_locales": bool(cambios) if cambios is not None else None,
        "huellas_scripts": {ruta.name: huella_archivo(ruta) for ruta in sorted(Path(__file__).parent.glob("*.py"))},
    }


def verificar_modelo(resultado: Any) -> None:
    afirmar(bool(resultado.mle_retvals.get("converged", False)), "el optimizador alcanzo convergencia")
    afirmar(bool(np.isfinite(np.asarray(resultado.params)).all()), "los parametros estimados son finitos")
    afirmar(bool(np.isfinite([resultado.llf, resultado.aic, resultado.bic]).all()), "los indicadores del ajuste son finitos")


def guardar_modelo(resultado: Any, ruta: Path) -> None:
    def escribir(archivo: Any) -> None:
        resultado.save(archivo)
        archivo.seek(0)
        recuperado = SARIMAXResults.load(archivo)
        afirmar(np.array_equal(np.asarray(resultado.params), np.asarray(recuperado.params)), "el modelo recuperado conserva exactamente sus parametros")
        afirmar(np.array_equal(np.asarray(resultado.forecast(1)), np.asarray(recuperado.forecast(1))), "el modelo recuperado produce el mismo pronostico de comprobacion")

    guardar_binario(ruta, escribir)


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION) -> dict[str, Any]:
    configuracion = cargar_configuracion(ruta_configuracion)
    rutas, opciones = configuracion["rutas"], configuracion["modelo"]
    raiz = Path(ruta_configuracion).resolve().parent
    avisos: list[dict[str, str]] = []
    capturadas: list[Any] = []
    banner("Etapa 4: ajuste SARIMA")
    try:
        datos, metadatos = cargar(rutas["ajuste"], "utf-8", configuracion["ingesta"]["separador"])
        exigir_preparacion(configuracion, ruta_configuracion, metadatos["sha256"])
        serie = construir_serie(datos, configuracion)
        with warnings.catch_warnings(record=True) as capturadas:
            warnings.simplefilter("always")
            modelo = SARIMAX(
                serie, order=tuple(opciones["orden"]), seasonal_order=tuple(opciones["orden_estacional"]),
                trend=opciones["tendencia"], enforce_stationarity=opciones["exigir_estacionariedad"],
                enforce_invertibility=opciones["exigir_invertibilidad"],
            )
            resultado = modelo.fit(method=opciones["metodo_optimizacion"], maxiter=opciones["iteraciones_maximas"], disp=False)
        avisos = [{"categoria": aviso.category.__name__, "mensaje": str(aviso.message)} for aviso in capturadas]
        verificar_modelo(resultado)
        guardar_modelo(resultado, rutas["modelo_ajustado"])
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, np.linalg.LinAlgError) as error:
        avisos = [{"categoria": aviso.category.__name__, "mensaje": str(aviso.message)} for aviso in capturadas]
        guardar_json({
            "etapa": "04_ajuste", "estado": "rechazado", "publicacion_autorizada": False,
            "error": str(error), "advertencias": avisos, "sha256_configuracion": huella_archivo(ruta_configuracion),
        }, rutas["reporte_ajuste"])
        raise

    reporte = {
        "etapa": "04_ajuste", "estado": "completada", "publicacion_autorizada": False,
        "periodo_ajuste": {"inicio": configuracion["periodos"]["inicio_ajuste"], "fin": configuracion["periodos"]["fin_ajuste"], "meses": len(serie)},
        "configuracion_modelo": opciones,
        "parametros_estimados": {nombre: float(valor) for nombre, valor in zip(resultado.param_names, resultado.params)},
        "convergencia": {"convergio": bool(resultado.mle_retvals["converged"]), "iteraciones": int(resultado.mle_retvals["iterations"])},
        "indicadores_ajuste": {"aic": float(resultado.aic), "bic": float(resultado.bic), "log_verosimilitud": float(resultado.llf)},
        "advertencias": avisos,
        "aleatoriedad": "No se utiliza muestreo ni inicializacion aleatoria. No se requiere semilla.",
        "verificacion_recuperacion": "Parametros y pronostico de comprobacion identicos al guardar y cargar.",
        "sha256_configuracion": huella_archivo(ruta_configuracion),
        "sha256_ajuste": metadatos["sha256"],
        "sha256_reporte_preparacion": huella_archivo(rutas["reporte_preparacion"]),
        "modelo": {"ruta": rutas["modelo_ajustado"].relative_to(raiz).as_posix(), "sha256": huella_archivo(rutas["modelo_ajustado"])},
        "versiones": {"python": platform.python_version(), **{nombre: importlib.metadata.version(nombre) for nombre in ("numpy", "pandas", "scipy", "statsmodels")}},
        "codigo": version_codigo(),
        "evaluacion_predictiva": "Pendiente. No se utilizaron los valores reservados para calcular errores ni seleccionar parametros.",
    }
    guardar_json(reporte, rutas["reporte_ajuste"])
    for aviso in avisos:
        print(f"[advertencia] {aviso['categoria']}: {aviso['mensaje']}", flush=True)
    print(f"[ok] Modelo ajustado con {len(serie)} meses y guardado. La evaluacion predictiva sigue pendiente.")
    return reporte


def main() -> None:
    parser = argparse.ArgumentParser(description="Ajustar SARIMA usando solo los meses de entrenamiento.")
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, np.linalg.LinAlgError) as error:
        parser.exit(1, f"[FALLO] Ajuste detenido: {error}\n")


if __name__ == "__main__":
    main()
