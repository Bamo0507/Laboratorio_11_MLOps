"""Datos y archivos de cada run, recogidos al completar la etapa que los produce."""

from __future__ import annotations

import importlib.metadata
import json
import platform
from importlib import import_module
from pathlib import Path
from typing import Any

from utils import afirmar, cargar_json, huella_archivo

# Se conservan reportes y series agregadas. No se copian microdatos al historial.
SALIDAS = {
    "01_ingesta.py": ("reporte_ingesta",),
    "02_validacion.py": ("reporte_validacion",),
    "03_preparacion.py": ("serie_mensual", "ajuste", "evaluacion", "reporte_preparacion"),
    "04_ajuste.py": ("modelo_ajustado", "reporte_ajuste"),
    "05_evaluacion.py": ("comparacion", "reporte_evaluacion"),
    "06_exportacion.py": ("candidato", "reporte_exportacion"),
    "07_publicacion.py": ("reporte_publicacion",),
    "08_monitoreo.py": ("reporte_monitoreo",),
}


def registrar_inicio(registro: Any, configuracion: dict, ruta_configuracion: Path) -> None:
    cliente, run_id = registro.cliente, registro.id_ejecucion
    raiz = ruta_configuracion.resolve().parent
    codigo = import_module("04_ajuste").version_codigo()
    afirmar(bool(codigo["commit"]), "se identifica el commit de Git del codigo ejecutado")
    cliente.set_tag(run_id, "mlflow.source.git.commit", codigo["commit"])
    cliente.set_tag(run_id, "codigo.cambios_locales", str(codigo["cambios_locales"]).lower())
    cliente.set_tag(run_id, "configuracion.sha256", huella_archivo(ruta_configuracion))
    cliente.log_dict(run_id, codigo, "codigo/version.json")
    for ruta in sorted(Path(__file__).parent.glob("*.py")):
        cliente.log_artifact(run_id, str(ruta), "codigo/src")
    for nombre in ("requirements.in", "requirements.txt", ".python-version"):
        ruta = Path(__file__).resolve().parents[1] / nombre
        cliente.log_artifact(run_id, str(ruta), "entorno")
    cliente.log_artifact(run_id, str(ruta_configuracion), "configuracion")
    # La copia normalizada tiene un nombre estable aunque se use --config con otro nombre.
    cliente.log_dict(run_id, {k: v for k, v in configuracion.items() if k != "rutas"}, "configuracion/parametros.json")
    for seccion in ("modelo", "periodos", "poblacion", "referencia", "evaluacion", "preparacion", "calidad", "seguimiento", "monitoreo"):
        for clave, valor in configuracion[seccion].items():
            cliente.log_param(run_id, f"{seccion}.{clave}", json.dumps(valor, ensure_ascii=False) if isinstance(valor, (list, dict, bool)) else valor)
    fuentes = []
    for nombre in ("entrenamiento", "prueba"):
        ruta = configuracion["rutas"][nombre]
        fuente = {"nombre": nombre, "archivo": ruta.relative_to(raiz).as_posix(), "disponible": ruta.is_file()}
        if fuente["disponible"]:
            fuente.update(sha256=huella_archivo(ruta), bytes=ruta.stat().st_size)
            cliente.log_param(run_id, f"fuente.{nombre}.sha256", fuente["sha256"])
        cliente.log_param(run_id, f"fuente.{nombre}.archivo", fuente["archivo"])
        fuentes.append(fuente)
    cliente.log_dict(run_id, {"fuentes": fuentes}, "datos/fuentes.json")
    versiones = {"python": platform.python_version(), **{n: importlib.metadata.version(n) for n in ("numpy", "pandas", "statsmodels", "scipy", "mlflow")}}
    cliente.log_dict(run_id, versiones, "entorno/versiones.json")
    registro.fuentes = fuentes


def guardar_archivo(registro: Any, ruta: Path, grupo: str) -> None:
    registro.cliente.log_artifact(registro.id_ejecucion, str(ruta), grupo)
    registro.cliente.set_tag(registro.id_ejecucion, f"archivo.{ruta.name}.sha256", huella_archivo(ruta))


def registrar_calidad(registro: Any, reporte: dict) -> None:
    for control in reporte["controles"]:
        registro.cliente.set_tag(registro.id_ejecucion, f"control.{control['codigo']}", control["estado"])
    registro.cliente.set_tag(registro.id_ejecucion, "calidad.estado", reporte["estado"])


def registrar_etapa(registro: Any, configuracion: dict, etapa: str) -> None:
    rutas = configuracion["rutas"]
    for nombre in SALIDAS[etapa]:
        ruta = rutas[nombre]
        grupo = "modelo" if nombre == "modelo_ajustado" else "reportes" if nombre.startswith("reporte_") else "estimaciones" if nombre == "candidato" else "datos"
        guardar_archivo(registro, ruta, grupo)
    if etapa == "01_ingesta.py":
        leidas = {f["archivo"]: f["sha256"] for f in cargar_json(rutas["reporte_ingesta"])["fuentes"]}
        afirmar(all(leidas.get(f["archivo"]) == f.get("sha256") for f in registro.fuentes), "las fuentes ingeridas coinciden con las registradas al iniciar el run")
    elif etapa == "02_validacion.py":
        registrar_calidad(registro, cargar_json(rutas["reporte_validacion"]))
    elif etapa == "04_ajuste.py":
        reporte = cargar_json(rutas["reporte_ajuste"])
        for nombre, valor in reporte["parametros_estimados"].items():
            registro.cliente.log_param(registro.id_ejecucion, f"estimado.{nombre}", valor)
    elif etapa == "05_evaluacion.py":
        reporte = cargar_json(rutas["reporte_evaluacion"])
        afirmar(reporte["estado"] == "completada", "solo se registran metricas de una evaluacion completada")
        for modelo, metricas in reporte["metricas"].items():
            for nombre, valor in metricas.items():
                registro.cliente.log_metric(registro.id_ejecucion, f"{modelo}.{nombre}", valor)
        registro.cliente.set_tag(registro.id_ejecucion, "desempeno.supera_regla", str(reporte["supera_regla_desempeno"]).lower())
    elif etapa == "06_exportacion.py":
        reporte = cargar_json(rutas["reporte_exportacion"])
        afirmar(reporte.get("id_ejecucion_mlflow") == registro.id_ejecucion, "la exportacion identifica el run que la produjo")
        registro.cliente.set_tag(registro.id_ejecucion, "exportacion.id_local", reporte["id_ejecucion_local"])
    elif etapa == "07_publicacion.py":
        reporte = cargar_json(rutas["reporte_publicacion"])
        registro.cliente.set_tag(registro.id_ejecucion, "publicacion", reporte["estado"])
        if reporte["estado"] == "publicado":
            from config import ARCHIVO_VIGENTE
            indicador = cargar_json(rutas["publicaciones"] / ARCHIVO_VIGENTE)
            guardar_archivo(registro, rutas["publicaciones"] / indicador["archivo"], "publicacion")
    elif etapa == "08_monitoreo.py":
        reporte = cargar_json(rutas["reporte_monitoreo"])
        registro.cliente.set_tag(registro.id_ejecucion, "monitoreo.estado", reporte["estado"])
        for verificacion in reporte["verificaciones"]:
            registro.cliente.set_tag(registro.id_ejecucion, f"monitoreo.{verificacion['codigo']}", verificacion["estado"])


def registrar_fallo_etapa(registro: Any, configuracion: dict, etapa: str, anterior: tuple | None) -> None:
    # La ingesta puede escribir un reporte de calidad bloqueado. No se reutiliza uno viejo.
    if etapa not in ("01_ingesta.py", "02_validacion.py"):
        return
    ruta = configuracion["rutas"]["reporte_validacion"]
    actual = (ruta.stat().st_mtime_ns, ruta.stat().st_size) if ruta.exists() else None
    if actual is not None and actual != anterior:
        reporte = cargar_json(ruta)
        guardar_archivo(registro, ruta, "reportes")
        registrar_calidad(registro, reporte)
