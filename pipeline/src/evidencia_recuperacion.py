"""Prueba controlada con datos sinteticos: alertas, fallo, correccion y restauracion de una version."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from mlflow.exceptions import MlflowException

from config import ARCHIVO_VIGENTE, RUTA_CONFIGURACION, cargar_configuracion, columnas_requeridas
from orquestacion import ejecutar
from publicacion import consultar_vigente
from restaurar import restaurar
from utils import afirmar, cargar_json, guardar_json, huella_archivo

# La demostracion vive en su propia carpeta; nunca escribe en las publicaciones reales.
CARPETA_DEMO = "demo_recuperacion"
SEMILLA = 20261101


def sintetica(configuracion: dict, crecimiento: float, ruido: float, semilla: int, dividir_mes: bool = False) -> dict[str, pd.DataFrame]:
    """Tendencia y estacionalidad anual multiplicativas con ruido de semilla fija, de 2023-01 a 2026-06.

    Con ruido muy bajo el optimizador puede no converger; las combinaciones usadas convergen en macOS y Linux.
    """
    col = configuracion["columnas"]
    fechas = pd.date_range("2023-01-01", "2026-06-01", freq="MS")
    perturbacion = np.random.default_rng(semilla).normal(0, ruido, len(fechas))
    valores = 200_000 * np.exp(crecimiento * np.arange(len(fechas)) + 0.25 * np.sin(2 * np.pi * fechas.month / 12) + perturbacion)
    filas = []
    for fecha, valor in zip(fechas, valores):
        fila = dict.fromkeys(columnas_requeridas(configuracion), "categoria")
        fila.update({col["fecha"]: fecha.strftime("%Y-%m-%d"), col["anio"]: str(fecha.year), col["mes"]: str(fecha.month),
                     col["pais"]: "El Salvador", col["tipo"]: "Turista", col["valor"]: str(float(valor))})
        filas.append(fila)
    datos = pd.DataFrame(filas)
    if dividir_mes:
        # Misma clave parcial con otra agrupacion de residencia: advertencia de calidad, sin cambiar el total del mes.
        agrupacion = next(c for c in col["clave_registro"] if c not in configuracion["calidad"]["clave_revision_parcial"])
        mitad = datos.iloc[[16]].copy()
        mitad[col["valor"]] = str(float(datos.at[16, col["valor"]]) / 2)
        datos.loc[16, col["valor"]] = mitad.iloc[0][col["valor"]]
        mitad[agrupacion] = "otra agrupacion"
        datos = pd.concat([datos.iloc[:17], mitad, datos.iloc[17:]], ignore_index=True)
    corte = datos[col["fecha"]] < configuracion["periodos"]["inicio_evaluacion"]
    return {"entrenamiento": datos[corte], "prueba": datos[~corte]}


def escribir(configuracion: dict, conjuntos: dict[str, pd.DataFrame]) -> None:
    for nombre, datos in conjuntos.items():
        configuracion["rutas"][nombre].parent.mkdir(parents=True, exist_ok=True)
        datos.to_csv(configuracion["rutas"][nombre], index=False)


def correr(ruta: Path, principal: dict, tipo: str) -> tuple[dict, bool]:
    """Ejecuta el pipeline completo y devuelve su registro de ejecucion."""
    try:
        ejecutar(ruta, destino_seguimiento=principal, tipo=tipo)
        detenido = False
    except subprocess.CalledProcessError:
        detenido = True
    registro = sorted(cargar_configuracion(ruta)["rutas"]["registros"].glob("*.json"))[-1]
    return cargar_json(registro), detenido


def resumen(registro: dict) -> dict:
    return {clave: registro[clave] for clave in ("id_ejecucion", "tipo_ejecucion", "estado", "inicio_utc", "fin_utc", "etapas_completadas", "advertencias", "errores", "publicacion")}


def verificar(ruta_configuracion: Path) -> dict:
    ruta_configuracion = Path(ruta_configuracion).resolve()
    principal = cargar_configuracion(ruta_configuracion)
    huellas = {n: huella_archivo(principal["rutas"][n]) for n in ("entrenamiento", "prueba")}
    vigente_real = principal["rutas"]["publicaciones"] / ARCHIVO_VIGENTE
    indicador_real = huella_archivo(vigente_real) if vigente_real.exists() else None
    raiz = principal["rutas"]["procesados"] / CARPETA_DEMO
    shutil.rmtree(raiz, ignore_errors=True)
    raiz.mkdir(parents=True)
    texto = ruta_configuracion.read_text(encoding="utf-8")
    afirmar("datos_sinteticos = false" in texto, "la configuracion base declara datos reales")
    ruta_demo = raiz / "configuracion.toml"
    ruta_demo.write_text(texto.replace("datos_sinteticos = false", "datos_sinteticos = true", 1), encoding="utf-8")
    demo = cargar_configuracion(ruta_demo)
    publicaciones = demo["rutas"]["publicaciones"]
    monitoreo = lambda: {v["codigo"]: v["alertas"] for v in cargar_json(demo["rutas"]["reporte_monitoreo"])["verificaciones"]}

    escribir(demo, sintetica(demo, 0.012, 0.05, SEMILLA))
    registro_a, detenido = correr(ruta_demo, principal, "recuperacion_version_a")
    afirmar(not detenido and registro_a["publicacion"]["estado"] == "publicado", "la primera actualizacion sintetica fue aprobada")
    version_a = consultar_vigente(publicaciones)

    datos_b = sintetica(demo, 0.03, 0.04, SEMILLA + 1, dividir_mes=True)
    escribir(demo, datos_b)
    registro_b, detenido = correr(ruta_demo, principal, "recuperacion_version_b")
    version_b = consultar_vigente(publicaciones)
    alertas_b = monitoreo()
    afirmar(not detenido and version_b["version"] != version_a["version"], "la segunda actualizacion reemplazo la version vigente")
    afirmar(bool(alertas_b["calidad"]) and bool(alertas_b["resultados"]), "el monitoreo alerto el cambio de calidad y la variacion elevada sin bloquear la publicacion")

    duplicada = {**datos_b, "prueba": pd.concat([datos_b["prueba"], datos_b["prueba"].iloc[[0]]], ignore_index=True)}
    escribir(demo, duplicada)
    registro_fallo, detenido = correr(ruta_demo, principal, "recuperacion_fallo")
    afirmar(detenido and registro_fallo["estado"] == "fallida", "el pipeline se detuvo ante la clave duplicada")
    afirmar(registro_fallo["etapas_completadas"] == ["01_ingesta.py"] and registro_fallo["publicacion"]["estado"] == "no_evaluada", "la detencion ocurrio en la validacion, antes de publicar")
    afirmar(consultar_vigente(publicaciones)["version"] == version_b["version"], "la ultima version aprobada sigue disponible despues del fallo")

    escribir(demo, datos_b)
    registro_c, detenido = correr(ruta_demo, principal, "recuperacion_corregida")
    version_c = consultar_vigente(publicaciones)
    afirmar(not detenido and version_c["version"] not in (version_a["version"], version_b["version"]), "la correccion produjo una nueva version aprobada")
    afirmar(all(np.isclose(c["valor"], b["valor"], rtol=principal["seguimiento"]["tolerancia_relativa"], atol=principal["seguimiento"]["tolerancia_absoluta"])
                for b, c in zip(version_b["estimaciones"], version_c["estimaciones"])), "con los datos corregidos se repiten las estimaciones de la version B")

    indicador = restaurar(publicaciones, version_a["version"][:12])
    afirmar(indicador["version_reemplazada"] == version_c["version"], "la restauracion reemplazo la version C por la A")
    afirmar(all((publicaciones / "versiones" / f"{v['version']}.json").exists() for v in (version_a, version_b, version_c)), "las tres versiones aprobadas siguen guardadas")
    afirmar(all(huella_archivo(principal["rutas"][n]) == h for n, h in huellas.items()), "los CSV originales permanecen intactos")
    afirmar((huella_archivo(vigente_real) if vigente_real.exists() else None) == indicador_real, "la prueba no modifico las publicaciones reales")

    evidencia = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "carpeta": raiz.relative_to(ruta_configuracion.parent).as_posix(),
        "datos": "Sinteticos con semilla fija; el tablero los identifica como demostracion.",
        "versiones": {nombre: {"version": v["version"], "fecha_generacion": v["fecha_generacion"], "mae": v["metricas"]["sarima"]["mae"]}
                      for nombre, v in (("A", version_a), ("B", version_b), ("C", version_c))},
        "pasos": [
            {"paso": "1. Primera version aprobada", **resumen(registro_a)},
            {"paso": "2. Actualizacion con alertas de calidad y variacion", "alertas_monitoreo": alertas_b, **resumen(registro_b)},
            {"paso": "3. Clave duplicada en la copia", "vigente_conservada": version_b["version"], **resumen(registro_fallo)},
            {"paso": "4. Correccion y nueva ejecucion", **resumen(registro_c)},
            {"paso": "5. Restauracion de la version A", "indicador": indicador},
        ],
        "originales_intactos": True, "publicaciones_reales_intactas": True,
    }
    guardar_json(evidencia, principal["rutas"]["evidencia_recuperacion"])
    return evidencia


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=RUTA_CONFIGURACION)
    argumentos = parser.parse_args()
    try:
        evidencia = verificar(argumentos.config)
    except (OSError, ValueError, KeyError, TypeError, MlflowException) as error:
        parser.exit(1, f"[FALLO] La prueba de recuperacion no se completo: {error}\n")
    print(json.dumps(evidencia["versiones"], indent=2))
    print(f"[ok] Version restaurada: A. Evidencia en {evidencia['carpeta']} y evidencia_recuperacion.json.")


if __name__ == "__main__":
    main()
