import type { ContinenteId } from "@/features/shared/datos/types"

/** Llegadas por continente y año (P1: volumen y % del total; P3: índice 2019 = 100). */
export type ContinenteAnual = {
  anio: number
  continente: ContinenteId
  viajeros: number
  porcentaje: number
  indice2019: number
  parcial: boolean
}
