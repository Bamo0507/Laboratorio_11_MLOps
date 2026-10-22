import fronterasAnual from "@/data/vias/fronteras-anual.json"
import paisesAereosAnual from "@/data/vias/paises-aereos-anual.json"
import viasAnual from "@/data/vias/vias-anual.json"

import type { FronteraAnual, PaisAereoAnual, ViaAnual } from "./types"

export async function getViasAnual(): Promise<ViaAnual[]> {
  return viasAnual as ViaAnual[]
}

export async function getFronterasAnual(): Promise<FronteraAnual[]> {
  return fronterasAnual as FronteraAnual[]
}

export async function getPaisesAereosAnual(): Promise<PaisAereoAnual[]> {
  return paisesAereosAnual as PaisAereoAnual[]
}
