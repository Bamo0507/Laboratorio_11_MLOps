"""Encadena las etapas y recoge exclusivamente los resultados del run actual."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import ARCHIVO_VIGENTE, RUTA_CONFIGURACION, cargar_configuracion
from registro_mlflow import registrar_etapa, registrar_fallo_etapa
from seguimiento import registrar_ejecucion
from utils import cargar_json, guardar_json

DIR_SRC = Path(__file__).resolve().parent
ETAPAS = ["01_ingesta.py", "02_validacion.py", "03_preparacion.py", "04_ajuste.py", "05_evaluacion.py", "06_exportacion.py", "07_publicacion.py", "08_monitoreo.py"]


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def advertencias(rutas: dict, etapa: str) -> list[str]:
    """Advertencias que la etapa dejo en su propio reporte."""
    if etapa == "02_validacion.py":
        return [f"{c['codigo']}: {a}" for c in cargar_json(rutas["reporte_validacion"])["controles"] for a in c["advertencias"]]
    if etapa == "04_ajuste.py":
        return [f"ajuste: {a}" for a in cargar_json(rutas["reporte_ajuste"])["advertencias"]]
    if etapa == "08_monitoreo.py":
        return [f"monitoreo.{v['codigo']}: {a}" for v in cargar_json(rutas["reporte_monitoreo"])["verificaciones"] for a in v["alertas"]]
    return []


def guardar_bitacora(registro, configuracion: dict, bitacora: dict) -> None:
    rutas = configuracion["rutas"]
    completadas = [paso["etapa"] for paso in bitacora["etapas"] if paso.get("estado") == "completada"]
    vigente = rutas["publicaciones"] / ARCHIVO_VIGENTE
    publicacion = cargar_json(rutas["reporte_publicacion"]) if "07_publicacion.py" in completadas else {}
    bitacora.update(fin_utc=ahora(), estado="fallida" if bitacora["errores"] else "completada", etapas_completadas=completadas,
                    publicacion={"estado": publicacion.get("estado", "no_evaluada"), "motivo": publicacion.get("motivo"),
                                 "version_vigente": cargar_json(vigente).get("version") if vigente.exists() else None})
    ruta = rutas["registros"] / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}_{registro.id_ejecucion}.json"
    guardar_json(bitacora, ruta)
    registro.cliente.log_dict(registro.id_ejecucion, bitacora, "ejecucion/registro.json")
    print(f"[ok] Registro de la ejecucion: {ruta}", flush=True)


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION, destino_seguimiento: dict | None = None, tipo: str = "pipeline") -> str:
    ruta_configuracion = Path(ruta_configuracion).resolve()
    configuracion = cargar_configuracion(ruta_configuracion)
    with registrar_ejecucion(configuracion, ruta_configuracion, destino_seguimiento, tipo) as registro:
        bitacora = {"id_ejecucion": registro.id_ejecucion, "tipo_ejecucion": tipo, "inicio_utc": ahora(),
                    "etapas": [], "advertencias": [], "errores": []}
        try:
            for etapa in ETAPAS:
                paso = {"etapa": etapa, "inicio_utc": ahora()}
                bitacora["etapas"].append(paso)
                registro.iniciar_etapa(etapa)
                ruta_calidad = configuracion["rutas"]["reporte_validacion"]
                anterior = (ruta_calidad.stat().st_mtime_ns, ruta_calidad.stat().st_size) if ruta_calidad.exists() else None
                comando = [sys.executable, str(DIR_SRC / etapa), "--config", str(ruta_configuracion)]
                if etapa == "06_exportacion.py":
                    comando.extend(["--id-ejecucion-mlflow", registro.id_ejecucion])
                resultado = subprocess.run(comando, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           text=True, encoding="utf-8", errors="replace",
                                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                print(resultado.stdout, end="", flush=True)
                registro.cliente.log_text(registro.id_ejecucion, resultado.stdout, f"logs/{etapa}.txt")
                paso["fin_utc"] = ahora()
                if resultado.returncode:
                    paso["estado"] = "fallida"
                    bitacora["errores"] = [f"{etapa}: {linea}" for linea in resultado.stdout.splitlines() if linea.startswith("[FALLO]")] \
                        or [f"{etapa} termino con codigo {resultado.returncode}."]
                    registrar_fallo_etapa(registro, configuracion, etapa, anterior)
                    raise subprocess.CalledProcessError(resultado.returncode, [etapa], output=resultado.stdout)
                registrar_etapa(registro, configuracion, etapa)
                registro.completar_etapa(etapa)
                paso["estado"] = "completada"
                bitacora["advertencias"].extend(advertencias(configuracion["rutas"], etapa))
        except BaseException as error:
            bitacora["errores"] = bitacora["errores"] or [f"{type(error).__name__}: {error}"]
            raise
        finally:
            guardar_bitacora(registro, configuracion, bitacora)
    return registro.id_ejecucion
