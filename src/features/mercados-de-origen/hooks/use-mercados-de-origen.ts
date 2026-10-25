"use client"

import { useMemo, useState } from "react"

import { CONTINENTES, NOMBRE_CONTINENTE } from "@/features/shared/datos/continentes"
import type { ContinenteId } from "@/features/shared/datos/types"

import type { ContinenteAnual } from "../types"

/** Un mercado con menos de este % del total en 2019 parte de una base pequeña y su índice se infla. */
export const PESO_MINIMO_MERCADO = 2
/** Diferencias de índice menores a esto no permiten nombrar un ganador: se reportan como empate. */
export const MARGEN_EMPATE = 5

export type BarraContinente = {
  continente: ContinenteId
  nombre: string
  viajeros: number
  porcentaje: number
}

export type PuntoRecuperacion = { anio: number } & Partial<Record<ContinenteId, number>>

export type Recuperacion = {
  continente: ContinenteId
  nombre: string
  indice: number
  viajeros: number
  viajeros2019: number
  peso2019: number
  basePequena: boolean
}

export function useMercadosDeOrigen(datos: ContinenteAnual[]) {
  const anios = useMemo(() => [...new Set(datos.map((d) => d.anio))].sort((a, b) => a - b), [datos])
  const anioParcial = useMemo(() => datos.find((d) => d.parcial)?.anio ?? null, [datos])
  const ultimoAnioCompleto = useMemo(
    () => Math.max(...datos.filter((d) => !d.parcial).map((d) => d.anio)),
    [datos]
  )

  const [anioSeleccionado, setAnioSeleccionado] = useState(ultimoAnioCompleto)

  // P1: continentes del año elegido, de mayor a menor.
  const barras = useMemo<BarraContinente[]>(
    () =>
      datos
        .filter((d) => d.anio === anioSeleccionado)
        .sort((a, b) => b.viajeros - a.viajeros)
        .map((d) => ({
          continente: d.continente,
          nombre: NOMBRE_CONTINENTE[d.continente],
          viajeros: d.viajeros,
          porcentaje: d.porcentaje,
        })),
    [datos, anioSeleccionado]
  )

  // P3: índice 2019 = 100 por año, sin el año parcial (medio año no es comparable).
  const serieRecuperacion = useMemo<PuntoRecuperacion[]>(() => {
    const porAnio = new Map<number, PuntoRecuperacion>()
    for (const d of datos) {
      if (d.parcial) continue
      const punto = porAnio.get(d.anio) ?? { anio: d.anio }
      punto[d.continente] = d.indice2019
      porAnio.set(d.anio, punto)
    }
    return [...porAnio.values()].sort((a, b) => a.anio - b.anio)
  }, [datos])

  const recuperacionFinal = useMemo<Recuperacion[]>(() => {
    const final = datos.filter((d) => d.anio === ultimoAnioCompleto)
    const base = datos.filter((d) => d.anio === 2019)
    return CONTINENTES.map((id) => {
      const actual = final.find((d) => d.continente === id)
      const base2019 = base.find((d) => d.continente === id)
      const peso2019 = base2019?.porcentaje ?? 0
      return {
        continente: id,
        nombre: NOMBRE_CONTINENTE[id],
        indice: actual?.indice2019 ?? 0,
        viajeros: actual?.viajeros ?? 0,
        viajeros2019: base2019?.viajeros ?? 0,
        peso2019,
        basePequena: peso2019 < PESO_MINIMO_MERCADO,
      }
    }).sort((a, b) => b.indice - a.indice)
  }, [datos, ultimoAnioCompleto])

  // La "mejor recuperación" solo se elige entre mercados con peso real: un índice
  // alto sobre una base de pocos miles de visitantes no es comparable.
  const mejorRecuperacion = recuperacionFinal.find((r) => !r.basePequena) ?? recuperacionFinal[0]
  // Mercados relevantes cuya recuperación está a menos de MARGEN_EMPATE puntos del mejor.
  const empatados = useMemo(
    () => recuperacionFinal.filter((r) => !r.basePequena && mejorRecuperacion.indice - r.indice < MARGEN_EMPATE),
    [recuperacionFinal, mejorRecuperacion]
  )
  const mercadoPrincipal = useMemo(
    () => [...recuperacionFinal].sort((a, b) => b.peso2019 - a.peso2019)[0],
    [recuperacionFinal]
  )
  const [continenteResaltado, setContinenteResaltado] = useState<ContinenteId>(mejorRecuperacion.continente)

  const kpis = useMemo(() => {
    const total = barras.reduce((suma, b) => suma + b.viajeros, 0)
    const esParcial = anioSeleccionado === anioParcial
    const anterior = datos.filter((d) => d.anio === anioSeleccionado - 1)
    const totalAnterior = anterior.reduce((suma, d) => suma + d.viajeros, 0)
    // Un año parcial no se compara contra un año completo.
    const variacion = !esParcial && totalAnterior > 0 ? ((total - totalAnterior) / totalAnterior) * 100 : null
    const principal = barras[0]
    const pesoAnterior = anterior.find((d) => d.continente === principal.continente)?.porcentaje
    const cambioPeso = !esParcial && pesoAnterior !== undefined ? principal.porcentaje - pesoAnterior : null
    return { total, variacion, esParcial, principal, cambioPeso }
  }, [barras, datos, anioSeleccionado, anioParcial])

  return {
    anios,
    anioParcial,
    ultimoAnioCompleto,
    anioSeleccionado,
    setAnioSeleccionado,
    barras,
    kpis,
    serieRecuperacion,
    recuperacionFinal,
    mejorRecuperacion,
    empatados,
    mercadoPrincipal,
    continenteResaltado,
    setContinenteResaltado,
  }
}
