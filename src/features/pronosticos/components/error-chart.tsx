"use client"

import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { formatoCompacto, formatoPersonas } from "@/features/shared/datos/formato"
import { PieFuente } from "@/features/shared/ui/pie-fuente"
import { UsoDirectivo } from "@/features/shared/ui/uso-directivo"

import type { PuntoPronostico } from "../hooks/use-pronosticos"
import { etiquetaMes } from "./prediccion-chart"

type Props = {
  errores: PuntoPronostico[]
  nombreModelo: string
}

const ALTO_GRAFICO = 280
const CONFIG = { error: { label: "Error" } }

export function ErrorChart({ errores, nombreModelo }: Props) {
  const subestima = errores.filter((e) => e.error! < 0).length
  // Ticks redondos y simétricos alrededor de cero.
  const maximo = Math.max(1, ...errores.map((e) => Math.abs(e.error!)))
  // Unos 3 ticks por lado, en pasos de 1, 2 o 5 × 10^n.
  const crudo = maximo / 3
  const magnitud = 10 ** Math.floor(Math.log10(crudo))
  const paso = ([1, 2, 5, 10].find((m) => m * magnitud >= crudo) ?? 10) * magnitud
  const extremo = Math.ceil(maximo / paso) * paso
  const ticksY = Array.from({ length: (2 * extremo) / paso + 1 }, (_, i) => -extremo + i * paso)
  // Un tick por año; si el periodo elegido es corto, se etiquetan meses.
  const enero = errores.filter((e) => e.fecha.endsWith("-01")).map((e) => e.fecha)
  const porAnio = enero.length >= 2

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">Error del pronóstico mes a mes</h2>
        </CardTitle>
        <CardDescription className="max-w-[75ch] text-sm leading-relaxed">
          {errores.length === 0
            ? "El periodo seleccionado no incluye meses de prueba. Amplía la selección en el gráfico de arriba."
            : `Entre ${etiquetaMes(errores[0].fecha)} y ${etiquetaMes(errores.at(-1)!.fecha)}, ${nombreModelo} subestimó las llegadas en ${subestima} de ${errores.length} meses.`}
        </CardDescription>
        <UsoDirectivo>ver si el modelo tiende a quedarse corto o a pasarse, para saber en qué dirección ajustar los planes que se basen en él.</UsoDirectivo>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 px-6">
        {errores.length === 0 ? (
          <p className="rounded-lg bg-muted px-4 py-6 text-center text-sm text-muted-foreground">Sin datos para esta selección.</p>
        ) : (
          <>
          <p className="text-xs font-medium text-muted-foreground">Diferencia en personas (estimado − observado)</p>
          <ChartContainer
            config={CONFIG}
            className="-mt-1 aspect-auto w-full"
            style={{ height: ALTO_GRAFICO }}
            role="img"
            aria-label={`${nombreModelo} subestimó en ${subestima} de ${errores.length} meses.`}
          >
            <BarChart data={errores} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid vertical={false} stroke="var(--border)" />
              <XAxis
                dataKey="fecha"
                ticks={porAnio ? enero : undefined}
                tickFormatter={(fecha: string) => (porAnio ? fecha.slice(0, 4) : etiquetaMes(fecha))}
                interval={porAnio ? 0 : "preserveStartEnd"}
                minTickGap={32}
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tick={{ fontSize: 12 }}
              />
              <YAxis
                domain={[-extremo, extremo]}
                ticks={ticksY}
                tickFormatter={(v: number) => (v > 0 ? `+${formatoCompacto(v)}` : v < 0 ? `−${formatoCompacto(-v)}` : "0")}
                width={56}
                tickLine={false}
                axisLine={false}
                tick={{ fontSize: 12 }}
              />
              <ReferenceLine y={0} stroke="var(--muted-foreground)" />
              <ChartTooltip
                cursor={{ fill: "var(--muted)" }}
                content={({ active, payload }) => {
                  const p = payload?.[0]?.payload as PuntoPronostico | undefined
                  if (!active || !p || p.error === null) return null
                  return (
                    <div className="rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                      <p className="font-medium">{etiquetaMes(p.fecha)}</p>
                      <p className="text-muted-foreground">
                        {p.error >= 0 ? "Sobreestimó" : "Subestimó"} por{" "}
                        <span className="font-data text-foreground">{formatoPersonas(Math.abs(p.error))}</span> personas
                      </p>
                    </div>
                  )
                }}
              />
              <Bar dataKey="error" isAnimationActive={false}>
                {errores.map((e) => (
                  <Cell key={e.fecha} fill={e.error! >= 0 ? "var(--divergente-positivo)" : "var(--divergente-negativo)"} />
                ))}
              </Bar>
            </BarChart>
          </ChartContainer>
          </>
        )}
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <p>
          Error = estimado − observado.{" "}
          <span className="font-medium" style={{ color: "var(--divergente-positivo)" }}>Azul, hacia arriba</span>: el
          modelo sobreestimó.{" "}
          <span className="font-medium" style={{ color: "var(--divergente-negativo)" }}>Naranja, hacia abajo</span>: el
          modelo subestimó.
        </p>
        <PieFuente extra="Predicciones: laboratorios 1 y 2." />
      </CardFooter>
    </Card>
  )
}
