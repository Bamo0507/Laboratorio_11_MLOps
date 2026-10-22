import continentesMensual from "@/data/temporadas/continentes-mensual.json"

import type { ContinenteMensual } from "./types"

export async function getContinentesMensual(): Promise<ContinenteMensual[]> {
  return continentesMensual as ContinenteMensual[]
}
