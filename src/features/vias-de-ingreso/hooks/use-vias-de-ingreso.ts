"use client"

import { useMemo, useState } from "react"

import type { ViaId } from "@/features/shared/datos/types"

import type { FronteraAnual, PaisAereoAnual, ViaAnual } from "../types"
import { NOMBRE_VIA, VIAS } from "../vias"

/** Una frontera con menos viajeros que esto en el año base infla su % de crecimiento. */
export const VOLUMEN_MINIMO_FRONTERA = 5000
export const ANIO_PRE_PANDEMIA = 2019
// Desde 2023 la base usa la misma agrupación de países; antes se recodifica en el pipeline.
export const ANIOS_POST_PANDEMIA = [2023, 2024, 2025]
/** Años de pandemia: como base del índice exageran cualquier crecimiento posterior. */
export const ANIOS_PANDEMIA = [2020, 2021]
const TOP_PAISES = 10

export type PuntoCrecimiento = { anio: number } & Partial<Record<ViaId, number>>

export type CrecimientoVia = { via: ViaId; nombre: string; indice: number | null }

export type VariacionFrontera = {
  frontera: string
  inicial: number
  final: number
  variacion: number
  /** Menos de VOLUMEN_MINIMO_FRONTERA en el año base: su % se infla y se muestra como contexto. */
  basePequena: boolean
}

export type BarraPais = {
  pais: string
  /** null = la categoría no tiene registro en 2019 (sin dato, no cero). */
  porcentajePre: number | null
  porcentajePost: number
  viajerosPre: number | null
  viajerosPost: number
}

export type Datos = { vias: ViaAnual[]; fronteras: FronteraAnual[]; paises: PaisAereoAnual[] }

export function useViasDeIngreso({ vias, fronteras, paises }: Datos) {
  // El año parcial no entra al rango: medio año no se compara contra años completos.
  const anios = useMemo(
    () => [...new Set(vias.filter((d) => !d.parcial).map((d) => d.anio))].sort((a, b) => a - b),
    [vias]
  )
  // Un año de pandemia no sirve como base del índice: queda fuera de "Desde".
  const aniosInicio = useMemo(() => anios.slice(0, -1).filter((a) => !ANIOS_PANDEMIA.includes(a)), [anios])
  const anioParcial = useMemo(() => vias.find((d) => d.parcial)?.anio ?? null, [vias])

  const [rango, setRango] = useState({ inicio: anios[0], fin: anios.at(-1)! })
  const [viaSeleccionada, setViaSeleccionada] = useState<ViaId>("aerea")
  const [anioPost, setAnioPost] = useState(ANIOS_POST_PANDEMIA.at(-1)!)

  const cambiarInicio = (inicio: number) => setRango((r) => ({ inicio, fin: Math.max(r.fin, inicio + 1) }))
  const cambiarFin = (fin: number) => setRango((r) => ({ inicio: Math.min(r.inicio, fin - 1), fin }))

  // P2 gráfico A: índice con el primer año del rango = 100.
  const serie = useMemo<PuntoCrecimiento[]>(() => {
    const base = new Map(vias.filter((d) => d.anio === rango.inicio).map((d) => [d.via, d.viajeros]))
    const porAnio = new Map<number, PuntoCrecimiento>()
    for (const d of vias) {
      if (d.parcial || d.anio < rango.inicio || d.anio > rango.fin) continue
      const b = base.get(d.via)
      if (!b) continue
      const punto = porAnio.get(d.anio) ?? { anio: d.anio }
      punto[d.via] = (d.viajeros / b) * 100
      porAnio.set(d.anio, punto)
    }
    return [...porAnio.values()].sort((a, b) => a.anio - b.anio)
  }, [vias, rango])

  // Índice al final del rango; null si la vía no tiene dato en alguno de los extremos.
  const crecimientoFinal = useMemo<CrecimientoVia[]>(() => {
    const ultimo = serie.find((p) => p.anio === rango.fin)
    return VIAS.map((via) => ({ via, nombre: NOMBRE_VIA[via], indice: ultimo?.[via] ?? null }))
  }, [serie, rango.fin])

  const mayorCrecimiento = useMemo(
    () =>
      crecimientoFinal
        .filter((c) => c.indice !== null)
        .sort((a, b) => b.indice! - a.indice!)[0] ?? null,
    [crecimientoFinal]
  )

  // P2 gráfico B: variación % de todas las fronteras de la vía con dato en ambos años.
  // Las de base pequeña se muestran, pero marcadas como contexto.
  const variacionFronteras = useMemo<VariacionFrontera[]>(() => {
    const deVia = fronteras.filter((d) => d.via === viaSeleccionada)
    const inicial = new Map(deVia.filter((d) => d.anio === rango.inicio).map((d) => [d.frontera, d.viajeros]))
    return deVia
      .filter((d) => d.anio === rango.fin)
      .flatMap((d) => {
        const base = inicial.get(d.frontera)
        if (!base) return []
        return [
          {
            frontera: d.frontera,
            inicial: base,
            final: d.viajeros,
            variacion: ((d.viajeros - base) / base) * 100,
            basePequena: base < VOLUMEN_MINIMO_FRONTERA,
          },
        ]
      })
      .sort((a, b) => Number(a.basePequena) - Number(b.basePequena) || b.variacion - a.variacion)
  }, [fronteras, viaSeleccionada, rango])

  // P4: top 10 países por aire del año post, comparados contra 2019 en % del total aéreo.
  const barrasPaises = useMemo<BarraPais[]>(() => {
    const pre = new Map(paises.filter((d) => d.anio === ANIO_PRE_PANDEMIA).map((d) => [d.pais, d]))
    return paises
      .filter((d) => d.anio === anioPost)
      .sort((a, b) => b.porcentaje - a.porcentaje)
      .slice(0, TOP_PAISES)
      .map((d) => ({
        pais: d.pais,
        porcentajePost: d.porcentaje,
        viajerosPost: d.viajeros,
        porcentajePre: pre.get(d.pais)?.porcentaje ?? null,
        viajerosPre: pre.get(d.pais)?.viajeros ?? null,
      }))
  }, [paises, anioPost])

  const kpis = useMemo(() => {
    const porcentajeAereo = (anio: number) => {
      const delAnio = vias.filter((d) => d.anio === anio)
      const total = delAnio.reduce((suma, d) => suma + d.viajeros, 0)
      const aerea = delAnio.find((d) => d.via === "aerea")?.viajeros ?? 0
      return total > 0 ? (aerea / total) * 100 : 0
    }
    return {
      porcentajeAereo: porcentajeAereo(rango.fin),
      porcentajeAereoInicio: porcentajeAereo(rango.inicio),
      paisPrincipal: barrasPaises[0],
    }
  }, [vias, rango, barrasPaises])

  return {
    anios,
    aniosInicio,
    anioParcial,
    rango,
    cambiarInicio,
    cambiarFin,
    viaSeleccionada,
    setViaSeleccionada,
    anioPost,
    setAnioPost,
    serie,
    crecimientoFinal,
    mayorCrecimiento,
    variacionFronteras,
    barrasPaises,
    kpis,
  }
}
