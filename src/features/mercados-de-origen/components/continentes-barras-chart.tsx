"use client"

import { Bar, BarChart, Cell, LabelList, XAxis, YAxis } from "recharts"

import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CHART_CONFIG_CONTINENTES } from "@/features/shared/datos/continentes"
import { formatoPersonas, formatoPorcentaje } from "@/features/shared/datos/formato"
import type { ContinenteId } from "@/features/shared/datos/types"
import { NotaQuiebre, PieFuente } from "@/features/shared/ui/pie-fuente"
import { UsoDirectivo } from "@/features/shared/ui/uso-directivo"

import type { BarraContinente } from "../hooks/use-mercados-de-origen"

type Props = {
  barras: BarraContinente[]
  anios: number[]
  anioParcial: number | null
  anioSeleccionado: number
  onCambiarAnio: (anio: number) => void
  continenteResaltado: ContinenteId
  onSeleccionarContinente: (continente: ContinenteId) => void
}

const ALTO_FILA = 52

function etiquetaAnio(anio: number, anioParcial: number | null) {
  return anio === anioParcial ? `${anio} (enero a junio)` : String(anio)
}

export function ContinentesBarrasChart({
  barras,
  anios,
  anioParcial,
  anioSeleccionado,
  onCambiarAnio,
  continenteResaltado,
  onSeleccionarContinente,
}: Props) {
  const principal = barras[0]
  const items = anios.map((anio) => ({ value: String(anio), label: etiquetaAnio(anio, anioParcial) })).reverse()

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">
            ¿De qué continente se recibe la mayor cantidad de turismo?
          </h2>
        </CardTitle>
        <CardDescription className="text-sm leading-relaxed">
          En {etiquetaAnio(anioSeleccionado, anioParcial)}, {principal.nombre} aportó el{" "}
          {formatoPorcentaje(principal.porcentaje)} de los visitantes internacionales.
          {anioSeleccionado === anioParcial &&
            " Como solo hay datos de enero a junio, el reparto puede cambiar al completar el año: cada mercado tiene su propia temporada."}
        </CardDescription>
        <UsoDirectivo>ver en qué mercados se concentra la demanda, para priorizar hacia dónde dirigir la promoción internacional.</UsoDirectivo>
        <CardAction>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            Año
            <Select
              items={items}
              value={String(anioSeleccionado)}
              onValueChange={(valor) => valor && onCambiarAnio(Number(valor))}
            >
              <SelectTrigger className="h-10 min-w-36 bg-card text-foreground" aria-label="Año">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {items.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
        </CardAction>
      </CardHeader>

      <CardContent className="px-6">
        <ChartContainer
          config={CHART_CONFIG_CONTINENTES}
          className="aspect-auto w-full"
          style={{ height: barras.length * ALTO_FILA }}
          role="img"
          aria-label={`En ${anioSeleccionado}: ${barras
            .map((b) => `${b.nombre} ${formatoPorcentaje(b.porcentaje)}`)
            .join(", ")} de los visitantes.`}
        >
          <BarChart data={barras} layout="vertical" margin={{ top: 0, right: 172, bottom: 0, left: 0 }} barCategoryGap={14}>
            <XAxis type="number" hide domain={[0, "dataMax"]} />
            <YAxis
              type="category"
              dataKey="continente"
              width={176}
              tickLine={false}
              axisLine={false}
              tick={({ x, y, payload }) => {
                const barra = barras.find((b) => b.continente === payload.value)
                const activo = payload.value === continenteResaltado
                return (
                  <text
                    x={Number(x) - 12}
                    y={Number(y)}
                    dy={5}
                    textAnchor="end"
                    className={activo ? "fill-foreground font-semibold" : "fill-muted-foreground"}
                    style={{ fontSize: 14 }}
                  >
                    {barra?.nombre}
                  </text>
                )
              }}
            />
            <ChartTooltip
              cursor={{ fill: "var(--muted)" }}
              content={({ active, payload }) => {
                const dato = payload?.[0]?.payload as BarraContinente | undefined
                if (!active || !dato) return null
                return (
                  <div className="rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                    <p className="font-medium">{dato.nombre}</p>
                    <p className="font-data text-muted-foreground">
                      {formatoPersonas(dato.viajeros)} visitantes · {formatoPorcentaje(dato.porcentaje)}
                    </p>
                  </div>
                )
              }}
            />
            <Bar
              dataKey="viajeros"
              barSize={24}
              radius={[0, 4, 4, 0]}
              className="cursor-pointer"
              onClick={(dato) => onSeleccionarContinente((dato as unknown as BarraContinente).continente)}
              isAnimationActive={false}
            >
              {barras.map((b) => (
                <Cell
                  key={b.continente}
                  fill={`var(--color-${b.continente})`}
                  stroke={b.continente === continenteResaltado ? "var(--foreground)" : "none"}
                  strokeWidth={b.continente === continenteResaltado ? 2 : 0}
                />
              ))}
              <LabelList
                dataKey="viajeros"
                position="right"
                offset={10}
                content={({ x, y, width, height, index }) => {
                  const b = barras[index ?? 0]
                  return (
                    <text
                      x={Number(x) + Number(width) + 10}
                      y={Number(y) + Number(height) / 2}
                      dy={5}
                      className="fill-foreground font-data"
                      style={{ fontSize: 14 }}
                    >
                      {formatoPersonas(b.viajeros)}
                      <tspan className="fill-muted-foreground"> · {formatoPorcentaje(b.porcentaje)}</tspan>
                    </text>
                  )
                }}
              />
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <p>Haz clic en una barra para ver cómo se ha recuperado ese continente en el gráfico de abajo.</p>
        <p>El porcentaje es sobre el total de visitantes del año. La barra con borde es el continente seleccionado.</p>
        <NotaQuiebre />
        <PieFuente />
      </CardFooter>
    </Card>
  )
}
