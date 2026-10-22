import type { ContinenteId } from "@/features/shared/datos/types"

/** Llegadas mensuales por continente (P6). viajeros = null significa "sin dato", no cero. */
export type ContinenteMensual = {
  fecha: string
  anio: number
  mes: number
  continente: ContinenteId
  viajeros: number | null
}
