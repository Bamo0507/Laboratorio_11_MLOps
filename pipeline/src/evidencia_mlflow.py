"""Consulta MLflow y demuestra dos corridas equivalentes y un fallo controlado."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow.exceptions import MlflowException
from statsmodels.tsa.statespace.sarimax import SARIMAXResults

from config import ARCHIVO_VIGENTE, RUTA_CONFIGURACION, cargar_configuracion
from orquestacion import ejecutar
from seguimiento import conectar
from utils import afirmar, guardar_json, huella_archivo


def comparar(cliente, primero: str, segundo: str, relativa: float, absoluta: float) -> dict:
    runs = [cliente.get_run(identificador) for identificador in (primero, segundo)]
    afirmar(all(r.info.status == "FINISHED" for r in runs), "ambas ejecuciones terminaron")
    parametros = [{k: v for k, v in r.data.params.items() if not k.startswith("estimado.")} for r in runs]
    afirmar(parametros[0] == parametros[1], "se utilizaron los mismos parametros, fuentes y periodos")
    afirmar(runs[0].data.tags["configuracion.sha256"] == runs[1].data.tags["configuracion.sha256"], "la configuracion es identica")
    afirmar(runs[0].data.tags["mlflow.source.git.commit"] == runs[1].data.tags["mlflow.source.git.commit"], "el commit de Git coincide")
    maximo_metricas = 0.0
    afirmar(set(runs[0].data.metrics) == set(runs[1].data.metrics) == {"sarima.mae", "sarima.rmse", "referencia.mae", "referencia.rmse"}, "ambas ejecuciones registraron las cuatro metricas")
    for nombre, valor in runs[0].data.metrics.items():
        otro = runs[1].data.metrics[nombre]
        afirmar(bool(np.isclose(valor, otro, rtol=relativa, atol=absoluta)), f"{nombre}: metricas equivalentes")
        maximo_metricas = max(maximo_metricas, abs(valor - otro))
    con_diferencias = {}
    with tempfile.TemporaryDirectory(prefix="lab11_comparacion_") as temporal:
        carpetas = []
        for i, identificador in enumerate((primero, segundo)):
            carpeta = Path(temporal) / str(i)
            carpeta.mkdir()
            cliente.download_artifacts(identificador, "", str(carpeta))
            carpetas.append(carpeta)
        codigos = [json.loads((c / "codigo/version.json").read_text()) for c in carpetas]
        afirmar(codigos[0]["huellas_scripts"] == codigos[1]["huellas_scripts"], "coinciden las huellas del codigo realmente ejecutado")
        for nombre in ("03_serie_mensual.csv", "03_ajuste.csv", "03_evaluacion.csv", "05_comparacion.csv"):
            tablas = [pd.read_csv(c / "datos" / nombre) for c in carpetas]
            afirmar(tablas[0].shape == tablas[1].shape and list(tablas[0].columns) == list(tablas[1].columns), f"{nombre}: misma estructura")
            diferencia = 0.0
            for columna in tablas[0].columns:
                a, b = tablas[0][columna], tablas[1][columna]
                if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
                    afirmar(bool(np.allclose(a, b, rtol=relativa, atol=absoluta, equal_nan=True)), f"{nombre}/{columna}: valores equivalentes")
                    delta = np.abs(a.to_numpy(dtype=float) - b.to_numpy(dtype=float))
                    diferencia = max(diferencia, float(np.nanmax(delta)) if not np.isnan(delta).all() else 0.0)
                else:
                    afirmar(a.equals(b), f"{nombre}/{columna}: etiquetas identicas")
            con_diferencias[nombre] = diferencia
        modelos = [SARIMAXResults.load(c / "modelo/04_modelo_sarima.pkl") for c in carpetas]
        afirmar(bool(np.allclose(modelos[0].params, modelos[1].params, rtol=relativa, atol=absoluta)), "los parametros del modelo guardado son equivalentes")
        controles = [{k: v for k, v in r.data.tags.items() if k.startswith("control.")} for r in runs]
        afirmar(controles[0] == controles[1] and len(controles[0]) == 6, "los seis controles tienen resultados equivalentes")
    return {"runs": [primero, segundo], "equivalentes": True,
            "tolerancia_relativa": relativa, "tolerancia_absoluta": absoluta,
            "diferencia_maxima_metricas": maximo_metricas, "diferencias_maximas_archivos": con_diferencias,
            "criterio": "abs(a-b) <= tolerancia_absoluta + tolerancia_relativa * abs(b). Ausencias historicas deben coincidir.",
            "explicacion": "El ajuste es determinista en este entorno. La tolerancia admite pequenas diferencias de coma flotante entre plataformas. Los identificadores, fechas y estados de Git se conservan como metadatos y no se usan como valores estimados."}


def listar_artefactos(cliente, run_id: str, prefijo: str = "") -> list[str]:
    resultado = []
    for archivo in cliente.list_artifacts(run_id, prefijo):
        if archivo.is_dir:
            resultado.extend(listar_artefactos(cliente, run_id, archivo.path))
        else:
            resultado.append(archivo.path)
    return resultado


def resumir(cliente, run) -> dict:
    return {"id_ejecucion": run.info.run_id, "estado": run.info.status,
            "inicio_utc": datetime.fromtimestamp(run.info.start_time / 1000, timezone.utc).isoformat(),
            "fin_utc": datetime.fromtimestamp(run.info.end_time / 1000, timezone.utc).isoformat() if run.info.end_time else None,
            "parametros": run.data.params, "metricas": run.data.metrics, "etiquetas": run.data.tags,
            "artefactos": listar_artefactos(cliente, run.info.run_id)}


def verificar(ruta_configuracion: Path) -> dict:
    configuracion = cargar_configuracion(ruta_configuracion)
    cliente, experimento = conectar(configuracion)
    huellas = {n: huella_archivo(configuracion["rutas"][n]) for n in ("entrenamiento", "prueba")}
    primero = ejecutar(ruta_configuracion)
    segundo = ejecutar(ruta_configuracion)
    opciones = configuracion["seguimiento"]
    comparacion = comparar(cliente, primero, segundo, opciones["tolerancia_relativa"], opciones["tolerancia_absoluta"])
    vigente = configuracion["rutas"]["publicaciones"] / ARCHIVO_VIGENTE
    anterior = huella_archivo(vigente) if vigente.exists() else None
    previos = {r.info.run_id for r in cliente.search_runs([experimento.experiment_id], filter_string="tags.tipo_ejecucion = 'fallo_controlado'", max_results=10000)}
    with tempfile.TemporaryDirectory(prefix="lab11_fallo_controlado_") as temporal:
        raiz = Path(temporal)
        copia_config = raiz / "configuracion.toml"
        shutil.copy2(ruta_configuracion, copia_config)
        copia = cargar_configuracion(copia_config)
        for nombre in ("entrenamiento", "prueba"):
            copia["rutas"][nombre].parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(configuracion["rutas"][nombre], copia["rutas"][nombre])
        datos = pd.read_csv(copia["rutas"]["entrenamiento"], dtype=str, keep_default_na=False)
        datos.drop(columns=[copia["columnas"]["valor"]]).to_csv(copia["rutas"]["entrenamiento"], index=False)
        try:
            ejecutar(copia_config, destino_seguimiento=configuracion, tipo="fallo_controlado")
        except subprocess.CalledProcessError:
            pass
        else:
            raise ValueError("El fallo controlado no fue detectado.")
    fallidos = [r for r in cliente.search_runs([experimento.experiment_id], filter_string="tags.tipo_ejecucion = 'fallo_controlado'", max_results=10000) if r.info.run_id not in previos]
    afirmar(len(fallidos) == 1 and fallidos[0].info.status == "FAILED", "la copia defectuosa genero un run fallido")
    fallido = fallidos[0]
    afirmar(not fallido.data.metrics, "el run fallido no tiene metricas de una evaluacion no realizada")
    afirmar(configuracion["columnas"]["valor"] in fallido.data.tags["error_causa"], "la causa identifica la columna ausente")
    afirmar(all(huella_archivo(configuracion["rutas"][n]) == h for n, h in huellas.items()), "los CSV originales permanecen intactos")
    afirmar((huella_archivo(vigente) if vigente.exists() else None) == anterior, "el fallo de la copia no reemplazo el indicador vigente")
    evidencia = {"fecha_consulta_utc": datetime.now(timezone.utc).isoformat(),
                 "experimento": experimento.name, "id_experimento": experimento.experiment_id,
                 "comparacion": comparacion, "fallo_controlado": {"run_id": fallido.info.run_id, "problema": f"Columna {configuracion['columnas']['valor']} ausente en una copia temporal", "originales_intactos": True, "vigente_conservado": True},
                 "consulta": [resumir(cliente, cliente.get_run(n)) for n in (primero, segundo, fallido.info.run_id)]}
    guardar_json(evidencia, configuracion["rutas"]["evidencia_mlflow"])
    # La evidencia se consulta desde el propio historial, ademas del archivo de entrega.
    for run_id in (primero, segundo, fallido.info.run_id):
        cliente.log_artifact(run_id, str(configuracion["rutas"]["evidencia_mlflow"]), "evidencia")
    return evidencia


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    parser.add_argument("--verificar", action="store_true", help="Ejecuta dos corridas completas y una prueba de fallo con copias temporales.")
    argumentos = parser.parse_args()
    try:
        if argumentos.verificar:
            evidencia = verificar(argumentos.config)
            print(json.dumps({"equivalentes": evidencia["comparacion"]["equivalentes"], "runs": evidencia["comparacion"]["runs"], "fallido": evidencia["fallo_controlado"]["run_id"]}, indent=2))
        else:
            configuracion = cargar_configuracion(argumentos.config)
            cliente, experimento = conectar(configuracion)
            for run in cliente.search_runs([experimento.experiment_id], order_by=["attributes.start_time DESC"], max_results=20):
                print(json.dumps({"id": run.info.run_id, "estado": run.info.status, "publicacion": run.data.tags.get("publicacion"), "metricas": run.data.metrics, "causa": run.data.tags.get("error_causa")}, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, MlflowException, subprocess.CalledProcessError) as error:
        parser.exit(1, f"[FALLO] No se pudo verificar MLflow: {error}\n")


if __name__ == "__main__":
    main()
