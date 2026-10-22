"use client"

import { useMemo, useState } from "react"

import { CONTINENTES, NOMBRE_CONTINENTE } from "@/features/shared/datos/continentes"
import type { ContinenteId } from "@/features/shared/datos/types"

import type { ContinenteMensual } from "../types"

export type PeriodoId = "pre" | "post"

export const PERIODOS: Record<PeriodoId, { etiqueta: string; corta: string; desde: number; hasta: number }> = {
  pre: { etiqueta: "2010 a 2019", corta: "Antes", desde: 2010, hasta: 2019 },
  post: { etiqueta: "2022 a 2025", corta: "Después", desde: 2022, hasta: 2025 },
}

export const MESES_LARGOS = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
export const INICIALES_MESES = "EFMAMJJASOND"

/** Si las llegadas se repartieran parejo en el año, cada mes tendría 100 / 12 = 8.3 %. */
export const MES_PROMEDIO = 100 / 12

/** Un pico es "claro" si ese mes fue el de más llegadas en más de la mitad de los años. */
export const PROPORCION_PICO_CLARO = 0.5

export type PuntoPerfil = { mes: number } & Record<string, number | [number, number]>

export type Extremos = {
  mesPico: number
  porcentajePico: number
  mesSegundo: number
  porcentajeSegundo: number
  picoClaro: boolean
  aniosConPico: number
  anios: number
  mesBajo: number
  porcentajeBajo: number
}

export type ResumenContinente = Extremos & { continente: ContinenteId; nombre: string }

type Perfil = {
  promedio: Record<number, number>
  minimo: Record<number, number>
  maximo: Record<number, number>
  anios: number
  picosPorAnio: number[]
}

/**
 * % de las llegadas anuales que cae en cada mes. Se promedia entre los años del periodo y se
 * guarda el mínimo y máximo para mostrar cuánto varía. Un año con algún mes sin dato no entra.
 */
function perfilMensual(registros: ContinenteMensual[], desde: number, hasta: number): Perfil {
  const porMes: Record<number, number[]> = {}
  const picosPorAnio: number[] = []
  let anios = 0
  for (let anio = desde; anio <= hasta; anio++) {
    const delAnio = registros.filter((r) => r.anio === anio)
    if (delAnio.length !== 12 || delAnio.some((r) => r.viajeros === null)) continue
    anios++
    const total = delAnio.reduce((suma, r) => suma + (r.viajeros ?? 0), 0)
    for (const r of delAnio) (porMes[r.mes] ??= []).push(((r.viajeros ?? 0) / total) * 100)
    picosPorAnio.push(delAnio.reduce((a, b) => ((b.viajeros ?? 0) > (a.viajeros ?? 0) ? b : a)).mes)
  }
  const resumir = (f: (v: number[]) => number) =>
    Object.fromEntries(Object.entries(porMes).map(([mes, v]) => [mes, f(v)])) as Record<number, number>
  return {
    promedio: resumir((v) => v.reduce((a, b) => a + b, 0) / v.length),
    minimo: resumir((v) => Math.min(...v)),
    maximo: resumir((v) => Math.max(...v)),
    anios,
    picosPorAnio,
  }
}

function extremos({ promedio, picosPorAnio }: Pick<Perfil, "promedio" | "picosPorAnio">): Extremos {
  const meses = Object.keys(promedio).map(Number).sort((a, b) => promedio[b] - promedio[a])
  const [mesPico, mesSegundo] = meses
  const mesBajo = meses[meses.length - 1]
  const aniosConPico = picosPorAnio.filter((m) => m === mesPico).length
  return {
    mesPico,
    porcentajePico: promedio[mesPico],
    mesSegundo,
    porcentajeSegundo: promedio[mesSegundo],
    picoClaro: aniosConPico / picosPorAnio.length > PROPORCION_PICO_CLARO,
    aniosConPico,
    anios: picosPorAnio.length,
    mesBajo,
    porcentajeBajo: promedio[mesBajo],
  }
}

/** Suma los continentes por mes. Si algún continente no tiene dato, el mes del país queda sin dato. */
function registrosPais(datos: ContinenteMensual[]): ContinenteMensual[] {
  const porMes = new Map<string, ContinenteMensual>()
  for (const d of datos) {
    const previo = porMes.get(d.fecha)
    const viajeros =
      (previo && previo.viajeros === null) || d.viajeros === null ? null : (previo?.viajeros ?? 0) + d.viajeros
    porMes.set(d.fecha, { ...d, viajeros })
  }
  return [...porMes.values()]
}

function perfilesPorContinente(datos: ContinenteMensual[], periodo: PeriodoId) {
  const { desde, hasta } = PERIODOS[periodo]
  return Object.fromEntries(
    CONTINENTES.map((id) => [id, perfilMensual(datos.filter((d) => d.continente === id), desde, hasta)])
  ) as Record<ContinenteId, Perfil>
}

export function useTemporadas(datos: ContinenteMensual[]) {
  const [periodo, setPeriodo] = useState<PeriodoId>("post")
  const otro: PeriodoId = periodo === "post" ? "pre" : "post"

  const todos = useMemo(
    () => ({ pre: perfilesPorContinente(datos, "pre"), post: perfilesPorContinente(datos, "post") }),
    [datos]
  )
  const perfiles = todos[periodo]

  // Formato ancho para Recharts: una fila por mes; <id> = promedio, <id>_rango = [mínimo, máximo].
  const serie = useMemo<PuntoPerfil[]>(
    () =>
      INICIALES_MESES.split("").map((_, i) => {
        const mes = i + 1
        const punto: PuntoPerfil = { mes }
        for (const id of CONTINENTES) {
          punto[id] = perfiles[id].promedio[mes]
          punto[`${id}_rango`] = [perfiles[id].minimo[mes], perfiles[id].maximo[mes]]
        }
        return punto
      }),
    [perfiles]
  )

  const resumen = useMemo<ResumenContinente[]>(
    () => CONTINENTES.map((id) => ({ continente: id, nombre: NOMBRE_CONTINENTE[id], ...extremos(perfiles[id]) })),
    [perfiles]
  )

  // Solo se reporta un cambio de temporada si el pico se repite en la mayoría de años de ambos periodos.
  const cambios = useMemo(
    () =>
      resumen
        .map((r) => ({ ...r, otro: extremos(todos[otro][r.continente]) }))
        .filter((r) => r.picoClaro && r.otro.picoClaro && r.otro.mesPico !== r.mesPico)
        .map((r) => ({ continente: r.continente, nombre: r.nombre, mesOtro: r.otro.mesPico, mes: r.mesPico })),
    [resumen, todos, otro]
  )

  // KPIs del país en ambos periodos (el otro sirve de comparación).
  const pais = useMemo(() => {
    const registros = registrosPais(datos)
    const calcular = (p: PeriodoId) => {
      const e = extremos(perfilMensual(registros, PERIODOS[p].desde, PERIODOS[p].hasta))
      return { ...e, razon: e.porcentajePico / e.porcentajeBajo }
    }
    return { actual: calcular(periodo), otro: calcular(otro) }
  }, [datos, periodo, otro])

  // Mismo eje en todos los paneles y en ambos periodos, para que la altura signifique lo mismo.
  const maximoY = useMemo(() => {
    const maximos = (["pre", "post"] as PeriodoId[]).flatMap((p) =>
      CONTINENTES.flatMap((id) => Object.values(todos[p][id].maximo))
    )
    return Math.ceil(Math.max(...maximos) / 5) * 5
  }, [todos])

  const aniosPorPeriodo = { pre: todos.pre.centro.anios, post: todos.post.centro.anios }

  return { periodo, setPeriodo, otro, serie, resumen, cambios, pais, maximoY, aniosPorPeriodo }
}
