import type { ChartConfig } from "@/components/ui/chart"
import type { ViaId } from "@/features/shared/datos/types"

// Orden fijo de las vías: el color sigue a la entidad, nunca a su posición.
export const VIAS: ViaId[] = ["aerea", "terrestre", "maritima"]

export const NOMBRE_VIA: Record<ViaId, string> = {
  aerea: "Aérea",
  terrestre: "Terrestre",
  maritima: "Marítima",
}

/** Config de shadcn/ui charts: expone --color-<id> a partir de los tokens de globals.css. */
export const CHART_CONFIG_VIAS = Object.fromEntries(
  VIAS.map((id) => [id, { label: NOMBRE_VIA[id], color: `var(--via-${id})` }])
) satisfies ChartConfig
