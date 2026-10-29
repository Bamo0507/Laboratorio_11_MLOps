"""
Etapa 2 del pipeline: VALIDACION DE CALIDAD
------------------------------------------------------------
Una sola responsabilidad: comprobar los seis controles antes de preparar o modelar.

  Lee : las rutas ingesta y reporte_ingesta de configuracion.toml
  Hace: - evalua contratos, cobertura, unicidad, faltantes, valores y metodologia
        - comprueba la trazabilidad de los archivos utilizados
        - registra advertencias y fallos, sin imputar ni borrar filas
  Escribe: reporte_validacion; validado solo si pasan los controles criticos

Ejecutar: python pipeline/src/02_validacion.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from config import RUTA_CONFIGURACION, cargar_configuracion
from utils import banner, cargar, guardar, guardar_json, huella_archivo
from validacion import evaluar, reporte_bloqueado


def trazabilidad(configuracion: dict[str, Any], raiz: Path, datos: Any, sha256: str) -> tuple[dict[str, Any], list[str]]:
    rutas = configuracion["rutas"]
    errores = []
    try:
        manifiesto = json.loads(rutas["reporte_ingesta"].read_text(encoding="utf-8"))
        if not isinstance(manifiesto, dict):
            raise ValueError("El manifiesto debe ser un objeto JSON.")
        if manifiesto.get("etapa") != "01_ingesta" or manifiesto.get("estado") != "completada":
            errores.append("El manifiesto no corresponde a una ingesta completada.")
        if manifiesto.get("sha256_salida") != sha256:
            errores.append("La huella de la ingesta no coincide con su manifiesto; volver a ejecutar la ingesta.")
        if manifiesto.get("filas_salida") != len(datos):
            errores.append("El numero de filas no coincide con el registrado durante la ingesta.")
        fuentes = {f["archivo"]: f for f in manifiesto["fuentes"]}
        esperadas = {rutas[k].relative_to(raiz).as_posix() for k in ("entrenamiento", "prueba")}
        if set(fuentes) != esperadas:
            errores.append("El manifiesto no identifica exactamente las fuentes configuradas.")
        origen = configuracion["ingesta"]["columna_origen"]
        if origen not in datos.columns or set(datos[origen]) != esperadas:
            errores.append("La procedencia de las filas no coincide con las fuentes configuradas.")
        for clave in ("entrenamiento", "prueba"):
            ruta = rutas[clave]
            nombre = ruta.relative_to(raiz).as_posix()
            fuente = fuentes.get(nombre, {})
            if fuente.get("sha256") != huella_archivo(ruta):
                errores.append(f"La fuente {nombre} cambio despues de la ingesta.")
            if origen in datos.columns and int(datos[origen].eq(nombre).sum()) != fuente.get("filas"):
                errores.append(f"El conteo de filas de {nombre} no coincide con su manifiesto.")
        return manifiesto, errores
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {}, [*errores, f"No se pudo verificar el manifiesto: {error}"]


def ejecutar(ruta_configuracion: Path = RUTA_CONFIGURACION) -> dict[str, Any]:
    configuracion = cargar_configuracion(ruta_configuracion)
    rutas = configuracion["rutas"]
    raiz = Path(ruta_configuracion).resolve().parent
    banner("Etapa 2: validacion de calidad")
    try:
        datos, metadatos = cargar(rutas["ingesta"], "utf-8", configuracion["ingesta"]["separador"])
    except (OSError, ValueError, TypeError, UnicodeError) as error:
        guardar_json(reporte_bloqueado(str(error)), rutas["reporte_validacion"])
        raise ValueError(f"La validacion no pudo leer la ingesta: {error}") from error

    manifiesto, incidencias = trazabilidad(configuracion, raiz, datos, metadatos["sha256"])
    resultado = evaluar(datos, configuracion, metadatos["sha256"], incidencias, manifiesto)
    resultado["sha256_configuracion"] = huella_archivo(Path(ruta_configuracion))
    resultado["fuentes"] = manifiesto.get("fuentes", [])
    if resultado["apto_para_preparacion"]:
        guardar(datos, rutas["validado"], separador=configuracion["ingesta"]["separador"])
        resultado["sha256_validado"] = huella_archivo(rutas["validado"])
        resultado["salida_validada"] = rutas["validado"].relative_to(raiz).as_posix()
    guardar_json(resultado, rutas["reporte_validacion"])
    for control in resultado["controles"]:
        print(f"[{control['estado']}] {control['nombre']}", flush=True)
        for mensaje in [*control["errores"], *control["advertencias"]]:
            print(f"  {mensaje}", flush=True)
    if not resultado["apto_para_preparacion"]:
        raise ValueError("Los controles criticos fallaron. No se reemplazo el CSV validado ni se publico una version.")
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluar los seis controles de calidad.")
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        ejecutar(argumentos.config)
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"[FALLO] Validacion detenida: {error}\n")


if __name__ == "__main__":
    main()
