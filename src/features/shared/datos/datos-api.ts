import metadatos from "@/data/metadatos.json"
import totalMensual from "@/data/general/total-mensual.json"

import type { LlegadaMensual, Metadatos } from "./types"

// Datos transversales: catálogos y total mensual (KPIs de cualquier sección).
// Los JSON de src/data se generan a partir de los resultados de los labs 1 y 2 (no se editan a mano).

export async function getMetadatos(): Promise<Metadatos> {
  return metadatos as Metadatos
}

export async function getTotalMensual(): Promise<LlegadaMensual[]> {
  return totalMensual
}
