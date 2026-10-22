import type { ContinenteId, ViaId } from "@/features/shared/datos/types"

/** Llegadas por vía y año (P2, gráfico A). */
export type ViaAnual = {
  anio: number
  via: ViaId
  viajeros: number
  parcial: boolean
}

/** Llegadas por frontera y año dentro de cada vía (P2, gráfico B). */
export type FronteraAnual = {
  anio: number
  via: ViaId
  frontera: string
  viajeros: number
  parcial: boolean
}

/** 20 países con más llegadas por aire en cada año, con su % del total aéreo (P4). */
export type PaisAereoAnual = {
  anio: number
  pais: string
  continente: ContinenteId
  viajeros: number
  porcentaje: number
  parcial: boolean
}
