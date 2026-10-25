"use client"

import { Bar, BarChart, Cell, LabelList, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { formatoPersonas, formatoPorcentaje } from "@/features/shared/datos/formato"
import type { ModeloId } from "@/features/shared/datos/types"
import { PieFuente } from "@/features/shared/ui/pie-fuente"
import { UsoDirectivo } from "@/features/shared/ui/uso-directivo"

import type { Metrica } from "../types"

type Props = {
  metricas: Metrica[]
  nombreSerie: string
  nombreModelo: Record<ModeloId, string>
  modeloSeleccionado: ModeloId
  onSeleccionarModelo: (modelo: ModeloId) => void
}

const ALTO_FILA = 56
const CONFIG = { mape: { label: "MAPE" } }

type Barra = Metrica & { nombre: string }

export function ErrorModelosChart({ metricas, nombreSerie, nombreModelo, modeloSeleccionado, onSeleccionarModelo }: Props) {
  const barras: Barra[] = metricas.map((m) => ({ ...m, nombre: nombreModelo[m.modelo] }))
  const [mejor, , peor] = barras

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">¿Qué modelo se equivoca menos?</h2>
        </CardTitle>
        <CardDescription className="max-w-[75ch] text-sm leading-relaxed">
          En {nombreSerie.toLowerCase()}, {mejor.nombre} se equivocó en promedio un {formatoPorcentaje(mejor.mape)} de lo
          que realmente llegó; {peor.nombre}, un {formatoPorcentaje(peor.mape)}.
        </CardDescription>
        <UsoDirectivo>elegir en qué pronóstico apoyarse al planificar, sabiendo cuánto se equivoca cada modelo.</UsoDirectivo>
      </CardHeader>

      <CardContent className="px-6">
        <ChartContainer
          config={CONFIG}
          className="aspect-auto w-full"
          style={{ height: barras.length * ALTO_FILA }}
          role="img"
          aria-label={`Error porcentual medio: ${barras.map((b) => `${b.nombre} ${formatoPorcentaje(b.mape)}`).join(", ")}.`}
        >
          <BarChart data={barras} layout="vertical" margin={{ top: 0, right: 80, bottom: 0, left: 0 }} barCategoryGap={14}>
            <XAxis type="number" hide domain={[0, "dataMax"]} />
            <YAxis
              type="category"
              dataKey="modelo"
              width={240}
              tickLine={false}
              axisLine={false}
              tick={({ x, y, payload }) => {
                const activo = payload.value === modeloSeleccionado
                return (
                  <text
                    x={Number(x) - 12}
                    y={Number(y)}
                    dy={5}
                    textAnchor="end"
                    className={activo ? "fill-foreground font-semibold" : "fill-muted-foreground"}
                    style={{ fontSize: 14 }}
                  >
                    {nombreModelo[payload.value as ModeloId]}
                  </text>
                )
              }}
            />
            <ChartTooltip
              cursor={{ fill: "var(--muted)" }}
              content={({ active, payload }) => {
                const dato = payload?.[0]?.payload as Barra | undefined
                if (!active || !dato) return null
                return (
                  <div className="rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                    <p className="font-medium">{dato.nombre}</p>
                    <p className="font-data text-muted-foreground">
                      {formatoPorcentaje(dato.mape)} de error · unas {formatoPersonas(dato.mae)} personas por mes
                    </p>
                  </div>
                )
              }}
            />
            <Bar
              dataKey="mape"
              barSize={24}
              radius={[0, 4, 4, 0]}
              className="cursor-pointer"
              onClick={(dato) => onSeleccionarModelo((dato as unknown as Barra).modelo)}
              isAnimationActive={false}
            >
              {barras.map((b) => (
                <Cell key={b.modelo} fill={b.modelo === modeloSeleccionado ? "var(--estimacion)" : "var(--contexto)"} />
              ))}
              <LabelList
                dataKey="mape"
                position="right"
                offset={10}
                className="fill-foreground font-data"
                style={{ fontSize: 14 }}
                formatter={(v) => formatoPorcentaje(Number(v))}
              />
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <p>
          Haz clic en una barra para ver ese modelo en los gráficos de abajo. Error porcentual medio (MAPE): cuánto se aleja
          el pronóstico, en promedio, como porcentaje de lo que realmente llegó.
        </p>
        <PieFuente extra="Predicciones: laboratorios 1 y 2." />
      </CardFooter>
    </Card>
  )
}
