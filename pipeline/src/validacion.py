"""Los seis controles de calidad, sin modificar ni imputar los datos de entrada."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import columnas_requeridas

CONTROLES = (
    ("columnas_tipos", "Columnas y tipos"),
    ("fechas_cobertura", "Fechas y cobertura"),
    ("unicidad", "Unicidad"),
    ("faltantes", "Valores faltantes"),
    ("valores_denominadores", "Valores y denominadores"),
    ("regla_metodologica", "Regla metodologica"),
)


def control(codigo: str, errores: list[str], advertencias: list[str], **detalles: Any) -> dict[str, Any]:
    return {
        "codigo": codigo,
        "nombre": dict(CONTROLES)[codigo],
        "estado": "error" if errores else "advertencia" if advertencias else "ok",
        "errores": errores,
        "advertencias": advertencias,
        "detalles": detalles,
    }


def reporte(controles: list[dict[str, Any]], **datos: Any) -> dict[str, Any]:
    apto = all(c["estado"] in ("ok", "advertencia") for c in controles)
    return {
        "etapa": "02_validacion",
        "estado": "apto_con_advertencias" if apto and any(c["advertencias"] for c in controles) else "apto" if apto else "rechazado",
        "apto_para_preparacion": apto,
        "publicacion_autorizada": False,
        "controles": controles,
        **datos,
    }


def reporte_bloqueado(motivo: str) -> dict[str, Any]:
    controles = [control("columnas_tipos", [f"No se pudo completar la lectura estructural: {motivo}"], [])]
    for codigo, nombre in CONTROLES[1:]:
        controles.append({
            "codigo": codigo, "nombre": nombre, "estado": "no_evaluado",
            "errores": [], "advertencias": [],
            "detalles": {"motivo": "La lectura o el contrato de columnas impidio evaluar este control."},
        })
    return reporte(controles)


def ausencia(serie: pd.Series, marcadores: set[str]) -> pd.Series:
    return serie.isna() | serie.astype("string").str.strip().str.casefold().isin(marcadores)


def ejemplos(datos: pd.DataFrame, limite: int) -> list[dict[str, Any]]:
    muestra = datos.head(limite).astype(object)
    return muestra.where(muestra.notna(), None).to_dict("records")


def meses_necesarios(configuracion: dict[str, Any]) -> dict[str, pd.PeriodIndex]:
    periodos = configuracion["periodos"]
    ajuste = pd.period_range(periodos["inicio_ajuste"], periodos["fin_ajuste"], freq="M")
    evaluacion = pd.period_range(periodos["inicio_evaluacion"], periodos["fin_evaluacion"], freq="M")
    referencia = evaluacion - configuracion["referencia"]["rezago_meses"]
    return {"ajuste": ajuste, "evaluacion": evaluacion, "referencia": referencia}


def evaluar(
    datos: pd.DataFrame,
    configuracion: dict[str, Any],
    huella_ingesta: str,
    incidencias_trazabilidad: list[str],
    manifiesto: dict[str, Any],
) -> dict[str, Any]:
    """Reune todos los hallazgos posibles antes de decidir si la etapa puede avanzar."""
    col = configuracion["columnas"]
    calidad = configuracion["calidad"]
    origen = configuracion["ingesta"]["columna_origen"]
    requeridas = [*columnas_requeridas(configuracion), origen]
    faltan_columnas = sorted(set(requeridas) - set(datos.columns))
    if faltan_columnas:
        return reporte_bloqueado(f"Faltan columnas indispensables: {faltan_columnas}")

    marcadores = {valor.strip().casefold() for valor in calidad["marcadores_ausencia"]} | {""}
    limite = calidad["limite_ejemplos"]
    vacios = {nombre: ausencia(datos[nombre], marcadores) for nombre in datos.columns}
    numeros = {
        alias: pd.to_numeric(datos[col[alias]].mask(vacios[col[alias]]), errors="coerce")
        for alias in ("anio", "mes", "valor")
    }
    errores_tipos = []
    conteo_incompatibles = {}
    for alias, serie in numeros.items():
        incompatible = ~vacios[col[alias]] & serie.isna()
        if alias in ("anio", "mes"):
            finitos = pd.Series(np.isfinite(serie.to_numpy(dtype=float, na_value=np.nan)), index=serie.index)
            incompatible |= ~vacios[col[alias]] & (~finitos | serie.where(finitos).mod(1).ne(0))
        conteo_incompatibles[col[alias]] = int(incompatible.sum())
        if incompatible.any():
            errores_tipos.append(f"{col[alias]} tiene {int(incompatible.sum())} valores incompatibles con su tipo numerico.")
    adicionales = sorted(set(datos.columns) - set(requeridas) - set(col.get("opcionales", [])))
    resultados = [control(
        "columnas_tipos", errores_tipos,
        [f"Columnas adicionales no utilizadas: {adicionales}"] if adicionales else [],
        columnas_requeridas=requeridas, tipos_incompatibles=conteo_incompatibles,
    )]

    fechas = pd.to_datetime(datos[col["fecha"]].mask(vacios[col["fecha"]]), format=calidad["formato_fecha"], errors="coerce")
    fecha_invalida = fechas.isna() | datos[col["fecha"]].ne(fechas.dt.strftime(calidad["formato_fecha"]))
    incoherente = fechas.notna() & (
        numeros["anio"].ne(fechas.dt.year) | numeros["mes"].ne(fechas.dt.month)
    )
    no_mensual = fechas.notna() & fechas.dt.day.ne(1)
    poblacion = configuracion["poblacion"]
    elegibles = datos[col["tipo"]].isin(poblacion["tipos_incluidos"]) & ~datos[col["pais"]].isin(poblacion["paises_excluidos"])
    meses_fila = fechas.dt.to_period("M")
    disponibles = pd.PeriodIndex(meses_fila[elegibles & fechas.notna()].unique()).sort_values()
    necesarios = meses_necesarios(configuracion)
    union_necesarios = necesarios["ajuste"].union(necesarios["evaluacion"]).union(necesarios["referencia"])
    sin_cobertura = {nombre: indice.difference(disponibles).astype(str).tolist() for nombre, indice in necesarios.items()}
    fuera = []
    if fechas.notna().any():
        historia = pd.period_range(fechas.min(), fechas.max(), freq="M")
        fuera = historia.difference(disponibles).difference(union_necesarios).astype(str).tolist()
    errores_fechas = []
    for mascara, mensaje in (
        (fecha_invalida, "fechas vacias, invalidas o con formato incompatible"),
        (incoherente, "registros cuyo anio o mes no coincide con Fecha"),
        (no_mensual, "fechas que no corresponden al primer dia del mes"),
    ):
        if mascara.any():
            errores_fechas.append(f"Hay {int(mascara.sum())} {mensaje}.")
    for nombre, meses in sin_cobertura.items():
        if meses:
            errores_fechas.append(f"Falta cobertura sin residentes para {nombre}: {meses}")
    resultados.append(control(
        "fechas_cobertura", errores_fechas,
        [f"Hay {len(fuera)} meses historicos sin cobertura fuera de los periodos requeridos."] if fuera else [],
        meses_sin_cobertura=sin_cobertura, meses_sin_cobertura_fuera_periodos=fuera,
        ejemplos_fechas=ejemplos(datos.loc[fecha_invalida | incoherente | no_mensual, [col["fecha"], col["anio"], col["mes"]]], limite),
        meses_requeridos={nombre: len(indice) for nombre, indice in necesarios.items()},
    ))

    clave = col["clave_registro"]
    repetidos = datos.duplicated(clave)
    involucrados = datos.duplicated(clave, keep=False)
    parcial = calidad["clave_revision_parcial"]
    coincidencias = datos.duplicated(parcial)
    filas_parciales = datos.duplicated(parcial, keep=False)
    resultados.append(control(
        "unicidad",
        [f"Hay {int(repetidos.sum())} registros adicionales repetidos bajo la clave completa."] if repetidos.any() else [],
        [f"Hay {int(coincidencias.sum())} coincidencias bajo la clave parcial; no se eliminan automaticamente."] if coincidencias.any() else [],
        clave_completa=clave, duplicados_completos=int(repetidos.sum()),
        filas_involucradas_completas=int(involucrados.sum()),
        grupos_completos=int(datos.loc[involucrados, clave].drop_duplicates().shape[0]),
        clave_parcial=parcial, coincidencias_parciales=int(coincidencias.sum()),
        filas_involucradas_parciales=int(filas_parciales.sum()),
        grupos_parciales=int(datos.loc[filas_parciales, parcial].drop_duplicates().shape[0]),
        ejemplos=ejemplos(datos.loc[filas_parciales | involucrados, clave], limite),
    ))

    criticos = {nombre: int(vacios[nombre].sum()) for nombre in requeridas if vacios[nombre].any()}
    permitidos = {nombre: int(mascara.sum()) for nombre, mascara in vacios.items() if nombre not in requeridas and mascara.any()}
    resultados.append(control(
        "faltantes", [f"Hay faltantes en columnas indispensables: {criticos}"] if criticos else [],
        [f"Hay faltantes permitidos en columnas que no usa el procedimiento: {permitidos}"] if permitidos else [],
        faltantes_criticos=criticos, faltantes_permitidos=permitidos,
        politica="No se imputan valores ni se eliminan filas por faltantes.",
    ))

    valores = numeros["valor"]
    finitos = pd.Series(np.isfinite(valores.to_numpy(dtype=float, na_value=np.nan)), index=datos.index)
    no_finitos = valores.notna() & ~finitos
    negativos = valores.lt(0) & finitos
    seleccion = elegibles & fechas.notna()
    mensual = valores[seleccion].groupby(meses_fila[seleccion]).sum(min_count=1)
    mensual_requerido = mensual.loc[mensual.index.intersection(union_necesarios)]
    meses_no_finitos = mensual_requerido.index[~np.isfinite(mensual_requerido.to_numpy(dtype=float))].astype(str).tolist()
    meses_no_positivos = mensual_requerido.index[mensual_requerido.le(0)].astype(str).tolist()
    errores_valores = []
    if no_finitos.any():
        errores_valores.append(f"Hay {int(no_finitos.sum())} conteos no finitos.")
    if negativos.any():
        errores_valores.append(f"Hay {int(negativos.sum())} conteos negativos.")
    if meses_no_finitos:
        errores_valores.append(f"Hay totales mensuales no finitos: {meses_no_finitos}")
    if configuracion["modelo"]["transformacion"] == "log" and meses_no_positivos:
        errores_valores.append(f"El logaritmo requiere totales mensuales positivos: {meses_no_positivos}")
    resultados.append(control(
        "valores_denominadores", errores_valores, [],
        negativos=int(negativos.sum()), no_finitos=int(no_finitos.sum()),
        registros_con_cero=int(valores.eq(0).sum()),
        meses_no_positivos=meses_no_positivos, meses_no_finitos=meses_no_finitos,
        denominadores={
            "mape": "No aplica; el procedimiento usa MAE y RMSE, sin division por el valor observado.",
            "meses_evaluacion_esperados": len(necesarios["evaluacion"]),
            "observaciones": "La cobertura impide evaluar con un conjunto vacio o incompleto.",
        },
    ))

    tipos_ajenos = sorted(set(datos.loc[~vacios[col["tipo"]], col["tipo"]]) - set(calidad["tipos_fuente"]))
    errores_regla = list(incidencias_trazabilidad)
    if poblacion["destino"] not in poblacion["paises_excluidos"]:
        errores_regla.append("La poblacion debe excluir a los residentes del pais de destino.")
    if not set(poblacion["tipos_incluidos"]) <= set(calidad["tipos_fuente"]):
        errores_regla.append("La poblacion incluye categorias ajenas al contrato de visitantes.")
    if configuracion["ingesta"].get("granularidad_fuente") != "mensual" or manifiesto.get("granularidad_fuente") != "mensual":
        errores_regla.append("La fuente y su manifiesto deben declarar granularidad mensual.")
    if no_mensual.any():
        errores_regla.append("La fuente mensual no puede contener fechas diarias dentro de un mes.")
    if tipos_ajenos:
        errores_regla.append(f"La fuente contiene categorias ajenas al contrato de visitantes: {tipos_ajenos}")
    resultados.append(control(
        "regla_metodologica", errores_regla, [],
        regla="Fuente mensual trazable y categorias Turista/Excursionista; cobertura y positividad sobre la poblacion sin residentes.",
        alcance="La validacion no demuestra el origen institucional por si sola; verifica el contrato documentado y las huellas de los archivos.",
        filas_poblacion_objetivo=int(elegibles.sum()),
        filas_residentes=int(datos[col["pais"]].isin(poblacion["paises_excluidos"]).sum()),
        preparacion="La exclusion de residentes se aplica a la vista de control. El CSV validado conserva todas las filas; la etapa de preparacion realizara el filtro.",
    ))
    return reporte(
        resultados, filas_entrada=len(datos), sha256_ingesta=huella_ingesta,
        periodos=configuracion["periodos"], poblacion=poblacion,
    )
