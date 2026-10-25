"use client"

import { useMemo, useState } from "react"

import type { LlegadaMensual, Metadatos, ModeloId, SerieId } from "@/features/shared/datos/types"

import type { Metrica, Prediccion } from "../types"

/** Meses de historia previos a la prueba que se muestran como contexto en la serie total. */
const INICIO_HISTORIA = "2019-01"

/** Vistas de la sección que se pueden mostrar u ocultar. */
export const VISTAS = [
  { id: "comparacion", nombre: "Error por modelo" },
  { id: "prediccion", nombre: "Estimado contra observado" },
  { id: "error", nombre: "Error mes a mes" },
  { id: "tabla", nombre: "Tabla de métricas" },
] as const
export type VistaId = (typeof VISTAS)[number]["id"]

export type PuntoPronostico = {
  fecha: string
  real: number
  prediccion: number | null
  banda: [number, number] | null
  error: number | null
}

export type Datos = {
  predicciones: Prediccion[]
  metricas: Metrica[]
  metadatos: Metadatos
  totalMensual: LlegadaMensual[]
}

export function usePronosticos({ predicciones, metricas, metadatos, totalMensual }: Datos) {
  const [serie, setSerieEstado] = useState<SerieId>("total")
  const [modelo, setModeloEstado] = useState<ModeloId>("lstm")
  // Índices del Brush del gráfico A; null = todo el periodo.
  const [rango, setRango] = useState<{ inicio: number; fin: number } | null>(null)
  const [vistas, setVistas] = useState<VistaId[]>(VISTAS.map((v) => v.id))

  // Recharts reinicia el Brush cuando cambian los datos: el rango se reinicia con él.
  const setSerie = (s: SerieId) => {
    setSerieEstado(s)
    setRango(null)
  }
  const setModelo = (m: ModeloId) => {
    setModeloEstado(m)
    setRango(null)
  }

  const nombreModelo = useMemo(
    () => Object.fromEntries(metadatos.modelos.map((m) => [m.id, m.nombre])) as Record<ModeloId, string>,
    [metadatos]
  )
  const nombreSerie = useMemo(
    () => Object.fromEntries(metadatos.series.map((s) => [s.id, s.nombre])) as Record<SerieId, string>,
    [metadatos]
  )

  const metricasSerie = useMemo(
    () => metricas.filter((m) => m.serie === serie).sort((a, b) => a.mape - b.mape),
    [metricas, serie]
  )
  const seleccionado = metricasSerie.find((m) => m.modelo === modelo)!
  // La LSTM no trae banda propia: se muestra ± su MAE como rango típico de error.
  const bandaPorMae = modelo === "lstm"

  const puntos = useMemo<PuntoPronostico[]>(() => {
    const prueba = predicciones
      .filter((p) => p.serie === serie && p.modelo === modelo)
      .map((p) => ({
        fecha: p.fecha,
        real: p.real,
        prediccion: p.prediccion,
        banda: bandaPorMae
          ? ([Math.max(0, p.prediccion - seleccionado.mae), p.prediccion + seleccionado.mae] as [number, number])
          : p.limiteInferior !== null && p.limiteSuperior !== null
            ? ([p.limiteInferior, p.limiteSuperior] as [number, number])
            : null,
        error: p.prediccion - p.real,
      }))
    // Solo la serie total tiene historia mensual; La Aurora arranca en el periodo de prueba.
    if (serie !== "total") return prueba
    const historia = totalMensual
      .filter((d) => d.fecha >= INICIO_HISTORIA && d.fecha <= metadatos.finEntrenamiento)
      .map((d) => ({ fecha: d.fecha, real: d.viajeros, prediccion: null, banda: null, error: null }))
    return [...historia, ...prueba]
  }, [predicciones, totalMensual, metadatos.finEntrenamiento, serie, modelo, bandaPorMae, seleccionado.mae])

  // Cobertura real: % de meses de prueba en que lo observado cayó dentro de la banda.
  const cobertura = useMemo(() => {
    const conBanda = puntos.filter((p) => p.prediccion !== null && p.banda)
    if (conBanda.length === 0) return null
    const dentro = conBanda.filter((p) => p.real >= p.banda![0] && p.real <= p.banda![1]).length
    return (dentro / conBanda.length) * 100
  }, [puntos])

  // Gráfico B: error mensual solo dentro del periodo elegido en A.
  const errores = useMemo(() => {
    const visibles = rango ? puntos.slice(rango.inicio, rango.fin + 1) : puntos
    return visibles.filter((p) => p.error !== null)
  }, [puntos, rango])

  return {
    serie,
    setSerie,
    modelo,
    setModelo,
    rango,
    setRango,
    nombreModelo,
    nombreSerie,
    finEntrenamiento: metadatos.finEntrenamiento,
    quiebre: metadatos.quiebre.fecha,
    vistas,
    setVistas,
    bandaPorMae,
    cobertura,
    puntos,
    errores,
    metricasSerie,
    mejor: metricasSerie[0],
    peor: metricasSerie.at(-1)!,
    seleccionado,
  }
}
