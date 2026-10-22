import metricas from "@/data/pronosticos/metricas.json"
import predicciones from "@/data/pronosticos/predicciones.json"

import type { Metrica, Prediccion } from "./types"

export async function getPredicciones(): Promise<Prediccion[]> {
  return predicciones as Prediccion[]
}

export async function getMetricas(): Promise<Metrica[]> {
  return metricas as Metrica[]
}
