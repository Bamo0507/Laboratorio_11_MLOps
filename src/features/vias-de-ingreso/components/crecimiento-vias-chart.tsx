"use client"

import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceDot, ReferenceLine, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { formatoIndice } from "@/features/shared/datos/formato"
import { NotaQuiebre, PieFuente } from "@/features/shared/ui/pie-fuente"
import type { ViaId } from "@/features/shared/datos/types"
import { UsoDirectivo } from "@/features/shared/ui/uso-directivo"

import type { CrecimientoVia, PuntoCrecimiento } from "../hooks/use-vias-de-ingreso"
import { CHART_CONFIG_VIAS, NOMBRE_VIA, VIAS } from "../vias"

type Props = {
  serie: PuntoCrecimiento[]
  crecimientoFinal: CrecimientoVia[]
  rango: { inicio: number; fin: number }
  anioParcial: number | null
  viaSeleccionada: ViaId
  onSeleccionarVia: (via: ViaId) => void
}

const ALTO_GRAFICO = 340

function descripcion(c: CrecimientoVia | undefined, rango: { inicio: number; fin: number }) {
  if (!c || c.indice === null) {
    return `La vía ${c ? NOMBRE_VIA[c.via].toLowerCase() : ""} no tiene registros para todo el rango ${rango.inicio} a ${rango.fin}.`
  }
  return `Por cada 100 visitantes que entraron por vía ${c.nombre.toLowerCase()} en ${rango.inicio}, en ${rango.fin} entraron ${formatoIndice(c.indice)}.`
}

export function CrecimientoViasChart({ serie, crecimientoFinal, rango, anioParcial, viaSeleccionada, onSeleccionarVia }: Props) {
  const seleccionada = crecimientoFinal.find((c) => c.via === viaSeleccionada)
  // Las líneas en gris se dibujan primero para que la seleccionada quede encima.
  const orden = [...VIAS.filter((id) => id !== viaSeleccionada), viaSeleccionada]
  const maximo = Math.max(100, ...serie.flatMap((p) => VIAS.map((id) => p[id] ?? 0)))
  const techo = Math.ceil(maximo / 50) * 50
  const ticksY = Array.from({ length: techo / 50 + 1 }, (_, i) => i * 50)
  const muestraPandemia = rango.inicio <= 2021 && rango.fin >= 2020

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">
            ¿Cómo ha sido el crecimiento relativo de cada vía de ingreso al país?
          </h2>
        </CardTitle>
        <CardDescription className="max-w-[75ch] text-sm leading-relaxed">{descripcion(seleccionada, rango)}</CardDescription>
        <UsoDirectivo>saber por qué vía crecen más las llegadas, como insumo para planificar la capacidad de aeropuertos, puestos fronterizos y puertos.</UsoDirectivo>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 px-6">
        <ToggleGroup
          aria-label="Vía a detallar"
          value={[viaSeleccionada]}
          onValueChange={(valor) => valor[0] && onSeleccionarVia(valor[0] as ViaId)}
          variant="outline"
          spacing={2}
          className="flex-wrap"
        >
          {VIAS.map((id) => (
            <ToggleGroupItem
              key={id}
              value={id}
              className="h-10 cursor-pointer gap-2 px-3 text-sm transition-colors duration-150 hover:border-foreground/30 hover:bg-accent/45 hover:text-foreground data-pressed:border-primary data-pressed:bg-accent data-pressed:font-medium data-pressed:text-accent-foreground data-pressed:hover:bg-accent"
            >
              <span aria-hidden className="size-2.5 rounded-full" style={{ backgroundColor: `var(--via-${id})` }} />
              {NOMBRE_VIA[id]}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>

        <p className="text-xs font-medium text-muted-foreground">Índice ({rango.inicio} = 100)</p>

        <ChartContainer
          config={CHART_CONFIG_VIAS}
          className="-mt-2 aspect-auto w-full"
          style={{ height: ALTO_GRAFICO }}
          role="img"
          aria-label={descripcion(seleccionada, rango)}
        >
          <LineChart data={serie} margin={{ top: 12, right: 112, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            {muestraPandemia && (
              <ReferenceArea
                x1={Math.max(2020, rango.inicio)}
                x2={Math.min(2021, rango.fin)}
                fill="var(--muted)"
                fillOpacity={1}
                label={{ value: "Pandemia", position: "insideTop", fill: "var(--muted-foreground)", fontSize: 12 }}
              />
            )}
            <XAxis
              dataKey="anio"
              type="number"
              domain={[rango.inicio, rango.fin]}
              allowDecimals={false}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fontSize: 13 }}
            />
            <YAxis domain={[0, techo]} ticks={ticksY} width={40} tickLine={false} axisLine={false} tick={{ fontSize: 13 }} />
            <ReferenceLine
              y={100}
              stroke="var(--muted-foreground)"
              strokeDasharray="4 4"
              strokeOpacity={0.6}
              label={{ value: `Nivel de ${rango.inicio}`, position: "insideTopLeft", fill: "var(--muted-foreground)", fontSize: 12 }}
            />
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const filas = [...payload].sort((a, b) => Number(b.value) - Number(a.value))
                return (
                  <div className="min-w-44 rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                    <p className="mb-1 font-medium">{label}</p>
                    {filas.map((fila) => {
                      const id = fila.dataKey as ViaId
                      return (
                        <p
                          key={id}
                          className={`flex items-center justify-between gap-4 ${id === viaSeleccionada ? "font-medium text-foreground" : "text-muted-foreground"}`}
                        >
                          <span className="flex items-center gap-2">
                            <span aria-hidden className="size-2 rounded-full" style={{ backgroundColor: `var(--via-${id})` }} />
                            {NOMBRE_VIA[id]}
                          </span>
                          <span className="font-data">{formatoIndice(Number(fila.value))}</span>
                        </p>
                      )
                    })}
                  </div>
                )
              }}
            />
            {orden.map((id) => {
              const activo = id === viaSeleccionada
              return (
                <Line
                  key={id}
                  dataKey={id}
                  type="linear"
                  stroke={activo ? `var(--color-${id})` : "var(--contexto)"}
                  strokeWidth={activo ? 2.5 : 1.5}
                  dot={false}
                  activeDot={activo ? { r: 5, strokeWidth: 2, stroke: "var(--card)" } : false}
                  className="cursor-pointer"
                  onClick={() => onSeleccionarVia(id)}
                  isAnimationActive={false}
                />
              )
            })}
            {/* Etiquetas directas al final de cada línea con dato. */}
            {crecimientoFinal
              .filter((c) => c.indice !== null)
              .map((c) => {
                const activo = c.via === viaSeleccionada
                return (
                  <ReferenceDot
                    key={`etiqueta-${c.via}`}
                    x={rango.fin}
                    y={c.indice!}
                    r={0}
                    ifOverflow="visible"
                    label={{
                      value: `${c.nombre} ${formatoIndice(c.indice!)}`,
                      position: "right",
                      offset: 10,
                      fontSize: activo ? 13 : 12,
                      fontWeight: activo ? 600 : 400,
                      fill: activo ? "var(--foreground)" : "var(--muted-foreground)",
                    }}
                  />
                )
              })}
          </LineChart>
        </ChartContainer>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <p>Haz clic en una vía para ver la variación de cada una de sus fronteras en el gráfico de abajo.</p>
        <p>
          Índice = visitantes del año ÷ visitantes de {rango.inicio} × 100. 2020 y 2021 no se ofrecen como año base: con
          tan pocos visitantes, cualquier crecimiento posterior se exagera. {anioParcial && `${anioParcial} no se incluye porque solo tiene datos de enero a junio.`}
        </p>
        <p>
          La vía marítima deja de tener registros de turistas y excursionistas desde 2017, por lo que el reparto entre
          vías cambia levemente ese año.
        </p>
        <NotaQuiebre />
        <PieFuente />
      </CardFooter>
    </Card>
  )
}
