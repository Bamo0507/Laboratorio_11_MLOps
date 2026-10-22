import type { ChartConfig } from "@/components/ui/chart"

import type { ContinenteId } from "./types"

// Orden fijo de los continentes: el color sigue a la entidad, nunca a su posición.
export const CONTINENTES: ContinenteId[] = ["centro", "norte", "europa", "sur", "asia", "resto"]

export const NOMBRE_CONTINENTE: Record<ContinenteId, string> = {
  norte: "América del Norte",
  centro: "Centroamérica",
  sur: "Sudamérica y el Caribe",
  europa: "Europa",
  asia: "Asia",
  resto: "Resto del mundo",
}

/** Nombres cortos para etiquetas directas dentro de los gráficos. */
export const NOMBRE_CORTO_CONTINENTE: Record<ContinenteId, string> = {
  norte: "Norteamérica",
  centro: "Centroamérica",
  sur: "Sudamérica",
  europa: "Europa",
  asia: "Asia",
  resto: "Resto",
}

/** Config de shadcn/ui charts: expone --color-<id> a partir de los tokens de globals.css. */
export const CHART_CONFIG_CONTINENTES = Object.fromEntries(
  CONTINENTES.map((id) => [id, { label: NOMBRE_CONTINENTE[id], color: `var(--continente-${id})` }])
) satisfies ChartConfig
