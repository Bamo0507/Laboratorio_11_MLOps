"""
Etapa 7 del pipeline: PUBLICACION CONTROLADA
------------------------------------------------------------
Una sola responsabilidad: activar una version solo si supera los controles.

  Lee : candidato, reporte_exportacion y certificados anteriores
  Hace: - comprueba integridad, calidad y coherencia de las estimaciones
        - bloquea candidatos que no superan la regla de desempeno
        - conserva versiones y cambia el indicador vigente de forma atomica
  Escribe: reporte_publicacion y, si corresponde, versiones y vigente.json

Ejecutar: python pipeline/src/07_publicacion.py
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any
from uuid import UUID

from config import ARCHIVO_VIGENTE, RUTA_CONFIGURACION, cargar_configuracion
from publicacion import bloqueo, consultar_vigente, preparar_version
from utils import afirmar, banner, cargar_json, guardar_json, huella_archivo

exportacion = import_module("06_exportacion")


def verificar_candidato(configuracion: dict[str, Any], ruta_configuracion: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    rutas = configuracion["rutas"]
    reporte = cargar_json(rutas["reporte_exportacion"])
    afirmar(reporte.get("estado") == "completada", "la exportacion termino correctamente")
    afirmar(reporte["sha256_configuracion"] == huella_archivo(ruta_configuracion), "la configuracion coincide con la exportacion")
    for nombre in ("comparacion", "reporte_evaluacion"):
        afirmar(reporte["entradas"][nombre] == huella_archivo(rutas[nombre]), f"{nombre}: coincide con la exportacion")
    afirmar(reporte["candidato"]["sha256"] == huella_archivo(rutas["candidato"])
            and reporte["candidato"]["ruta"] == rutas["candidato"].relative_to(ruta_configuracion.resolve().parent).as_posix(),
            "el candidato coincide con la exportacion certificada")
    evaluada, datos = exportacion.verificar_entradas(configuracion, ruta_configuracion)
    candidato = cargar_json(rutas["candidato"])
    afirmar(candidato.get("version_esquema") == 1 and candidato.get("tipo") == "estimaciones_evaluadas"
            and candidato.get("publicacion_autorizada") is False, "el archivo es un candidato pendiente de publicacion")
    for campo, esperado in (("poblacion", configuracion["poblacion"]), ("modelo", configuracion["modelo"]),
                            ("referencia", configuracion["referencia"]), ("estimaciones", datos.to_dict(orient="records"))):
        afirmar(candidato.get(campo) == esperado, f"{campo}: el candidato conserva los datos certificados")
    for campo in ("periodo", "regla", "metricas", "metodo", "transformacion_inversa", "limitacion"):
        afirmar(candidato.get(campo) == evaluada[campo], f"{campo}: coincide con la evaluacion")
    decision = evaluada["supera_regla_desempeno"]
    afirmar(type(candidato.get("supera_regla_desempeno")) is bool and candidato["supera_regla_desempeno"] == decision
            and type(reporte.get("supera_regla_desempeno")) is bool and reporte["supera_regla_desempeno"] == decision,
            "el candidato y su reporte conservan la decision de desempeno")
    afirmar(candidato["trazabilidad"] == {"sha256_configuracion": huella_archivo(ruta_configuracion), "entradas": reporte["entradas"]},
            "la trazabilidad del candidato coincide con los certificados")
    afirmar(reporte["estimaciones"] == len(datos), "el numero de estimaciones coincide con la exportacion")
    UUID(reporte["id_ejecucion_local"])
    fecha = datetime.fromisoformat(reporte["fecha_generacion"])
    afirmar(fecha.tzinfo is not None, "la fecha de generacion incluye zona horaria")
    return candidato, reporte


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION) -> dict[str, Any]:
    ruta_configuracion = Path(ruta_configuracion)
    configuracion = cargar_configuracion(ruta_configuracion)
    rutas = configuracion["rutas"]
    banner("Etapa 7: decision de publicacion")
    try:
        candidato, exportada = verificar_candidato(configuracion, ruta_configuracion)
        with bloqueo(rutas["publicaciones"]):
            anterior = consultar_vigente(rutas["publicaciones"])
            resultado = {"etapa": "07_publicacion", "estado": "no_publicado", "publicacion_autorizada": False,
                         "id_ejecucion_local": exportada["id_ejecucion_local"],
                         "sha256_candidato": huella_archivo(rutas["candidato"]),
                         "sha256_reporte_exportacion": huella_archivo(rutas["reporte_exportacion"]),
                         "version_anterior": anterior["version"] if anterior else None,
                         "version_vigente": anterior["version"] if anterior else None,
                         "motivo": "SARIMA no supera la regla de desempeno.",
                         "estimaciones_disponibles": anterior is not None}
            indicador = None
            if candidato["supera_regla_desempeno"]:
                version = hashlib.sha256((resultado["sha256_candidato"] + resultado["sha256_reporte_exportacion"]).encode()).hexdigest()
                contenido = {**candidato, "publicacion_autorizada": True, "version": version,
                             "id_ejecucion_local": exportada["id_ejecucion_local"],
                             "tipo_identificador": "exportacion_local_pendiente_de_vincular_a_mlflow",
                             "fecha_generacion": exportada["fecha_generacion"],
                             "motivo": "Controles de calidad, integridad y desempeno superados.",
                             "estimaciones": [{**fila, "destino": configuracion["poblacion"]["destino"],
                                               "unidad": configuracion["poblacion"]["unidad"],
                                               "valor": fila["sarima"], "version_procedimiento": version,
                                               "id_ejecucion_local": exportada["id_ejecucion_local"],
                                               "fecha_generacion": exportada["fecha_generacion"]}
                                              for fila in candidato["estimaciones"]]}
                indicador = preparar_version(rutas["publicaciones"], contenido)
                resultado.update(estado="publicado", publicacion_autorizada=True, version_vigente=version,
                                 estimaciones_disponibles=True, motivo="Version aprobada y activada.")
            guardar_json(resultado, rutas["reporte_publicacion"])
            if indicador is not None:
                # Punto de activacion: el cambio atomico de vigente es la ultima escritura.
                guardar_json(indicador, rutas["publicaciones"] / ARCHIVO_VIGENTE)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, FloatingPointError) as error:
        guardar_json({"etapa": "07_publicacion", "estado": "rechazado", "publicacion_autorizada": False,
                      "error": str(error)}, rutas["reporte_publicacion"])
        raise
    print(f"[ok] Decision: {resultado['estado']}. Estimaciones aprobadas disponibles: {resultado['estimaciones_disponibles']}.")
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description="Publicar solo candidatos aprobados, conservando la version anterior.")
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, FloatingPointError) as error:
        parser.exit(1, f"[FALLO] Publicacion detenida: {error}\n")


if __name__ == "__main__":
    main()
