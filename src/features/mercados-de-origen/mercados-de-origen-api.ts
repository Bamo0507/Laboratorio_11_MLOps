import continentesAnual from "@/data/mercados/continentes-anual.json"

import type { ContinenteAnual } from "./types"

export async function getContinentesAnual(): Promise<ContinenteAnual[]> {
  return continentesAnual as ContinenteAnual[]
}
