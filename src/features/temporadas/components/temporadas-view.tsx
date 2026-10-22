"use client"

import type { ContinenteMensual } from "../types"
import { PERIODOS, useTemporadas } from "../hooks/use-temporadas"
import { KpisTemporadas } from "./kpis-temporadas"
import { TemporadasMultiplesChart } from "./temporadas-multiples-chart"

export function TemporadasView({ datos }: { datos: ContinenteMensual[] }) {
  const t = useTemporadas(datos)

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <p className="max-w-[70ch] text-base leading-relaxed text-muted-foreground">
        En qué meses llegan más y menos visitantes internacionales, y si esa temporada es la misma para cada
        continente. Compara el periodo antes y después de la pandemia para ver si la temporada cambió.
      </p>

      <KpisTemporadas
        etiquetaPeriodo={PERIODOS[t.periodo].etiqueta}
        etiquetaOtro={`${PERIODOS[t.otro].corta} (${PERIODOS[t.otro].etiqueta})`}
        actual={t.pais.actual}
        otro={t.pais.otro}
      />

      <TemporadasMultiplesChart
        periodo={t.periodo}
        onCambiarPeriodo={t.setPeriodo}
        otro={t.otro}
        serie={t.serie}
        resumen={t.resumen}
        cambios={t.cambios}
        maximoY={t.maximoY}
        aniosPorPeriodo={t.aniosPorPeriodo}
      />
    </div>
  )
}
