"use client"

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"

import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { formatoPersonas, formatoPorcentaje } from "@/features/shared/datos/formato"
import { NotaQuiebre, PieFuente } from "@/features/shared/ui/pie-fuente"
import { UsoDirectivo } from "@/features/shared/ui/uso-directivo"

import { ANIO_PRE_PANDEMIA, ANIOS_POST_PANDEMIA, type BarraPais } from "../hooks/use-vias-de-ingreso"

type Props = {
  barras: BarraPais[]
  anioPost: number
  onCambiarAnio: (anio: number) => void
}

const ALTO_FILA = 52

export function PaisesAereosChart({ barras, anioPost, onCambiarAnio }: Props) {
  const config = {
    porcentajePre: { label: String(ANIO_PRE_PANDEMIA), color: "var(--periodo-pre)" },
    porcentajePost: { label: String(anioPost), color: "var(--periodo-post)" },
  } satisfies ChartConfig
  const items = ANIOS_POST_PANDEMIA.map((a) => ({ value: String(a), label: String(a) })).reverse()
  const sinEquivalente = barras.filter((b) => b.porcentajePre === null).map((b) => b.pais)
  const principal = barras[0]
  const techo = Math.ceil(Math.max(0, ...barras.map((b) => Math.max(b.porcentajePre ?? 0, b.porcentajePost))) / 10) * 10
  const ticksX = Array.from({ length: techo / 10 + 1 }, (_, i) => i * 10)

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">
            ¿Cambiaron los países de los que más llegan visitantes por aire, antes y después de la pandemia?
          </h2>
        </CardTitle>
        <CardDescription className="max-w-[75ch] text-sm leading-relaxed">
          {principal &&
            `En ${anioPost}, ${principal.pais} aportó el ${formatoPorcentaje(principal.porcentajePost)} de las llegadas aéreas${principal.porcentajePre === null ? "" : `, frente a ${formatoPorcentaje(principal.porcentajePre)} en ${ANIO_PRE_PANDEMIA}`}.`}
          {sinEquivalente.length > 0 &&
            ` ${sinEquivalente.join(", ")} no ${sinEquivalente.length === 1 ? "tiene" : "tienen"} registro en ${ANIO_PRE_PANDEMIA} (sin dato, no cero).`}
        </CardDescription>
        <UsoDirectivo>detectar qué países ganaron o perdieron peso en las llegadas aéreas, como insumo para gestionar rutas y conectividad aérea.</UsoDirectivo>
        <CardAction>
          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            Año a comparar
            <Select items={items} value={String(anioPost)} onValueChange={(v) => v && onCambiarAnio(Number(v))}>
              <SelectTrigger className="h-10 min-w-24 bg-card text-foreground" aria-label="Año a comparar">
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

      <CardContent className="flex flex-col gap-3 px-6">
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          {(["porcentajePre", "porcentajePost"] as const).map((k) => (
            <span key={k} className="flex items-center gap-2">
              <span aria-hidden className="size-3 rounded-sm" style={{ backgroundColor: config[k].color }} />
              {config[k].label}
            </span>
          ))}
        </div>
        <ChartContainer
          config={config}
          className="aspect-auto w-full"
          style={{ height: barras.length * ALTO_FILA }}
          role="img"
          aria-label={barras
            .map((b) => `${b.pais}: ${b.porcentajePre === null ? "sin dato" : formatoPorcentaje(b.porcentajePre)} en ${ANIO_PRE_PANDEMIA}, ${formatoPorcentaje(b.porcentajePost)} en ${anioPost}`)
            .join(". ")}
        >
          <BarChart data={barras} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }} barGap={2}>
            <CartesianGrid horizontal={false} stroke="var(--border)" />
            <XAxis
              type="number"
              domain={[0, techo]}
              ticks={ticksX}
              tickFormatter={(v) => `${v} %`}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12 }}
            />
            <YAxis type="category" dataKey="pais" width={170} tickLine={false} axisLine={false} tick={{ fontSize: 13 }} />
            <ChartTooltip
              cursor={{ fill: "var(--muted)" }}
              content={({ active, payload }) => {
                const dato = payload?.[0]?.payload as BarraPais | undefined
                if (!active || !dato) return null
                return (
                  <div className="rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                    <p className="font-medium">{dato.pais}</p>
                    <p className="font-data text-muted-foreground">
                      {ANIO_PRE_PANDEMIA}:{" "}
                      {dato.porcentajePre === null || dato.viajerosPre === null
                        ? "sin dato"
                        : `${formatoPorcentaje(dato.porcentajePre)} · ${formatoPersonas(dato.viajerosPre)}`}
                    </p>
                    <p className="font-data text-foreground">
                      {anioPost}: {formatoPorcentaje(dato.porcentajePost)} · {formatoPersonas(dato.viajerosPost)}
                    </p>
                  </div>
                )
              }}
            />
            <Bar dataKey="porcentajePre" fill="var(--color-porcentajePre)" barSize={14} radius={[0, 3, 3, 0]} isAnimationActive={false} />
            <Bar dataKey="porcentajePost" fill="var(--color-porcentajePost)" barSize={14} radius={[0, 3, 3, 0]} isAnimationActive={false} />
          </BarChart>
        </ChartContainer>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <p>
          Porcentaje sobre el total de llegadas aéreas de cada año: así se comparan años con totales distintos. Ordenado
          por {anioPost}.
        </p>
        <p>
          Desde 2023 la base agrupa a los países con menos llegadas en «Otros Países de América del Sur», «Otros Países de
          Europa» y «Resto del Mundo». Para comparar, los países de {ANIO_PRE_PANDEMIA} se agruparon de la misma forma.
        </p>
        <NotaQuiebre />
        <PieFuente />
      </CardFooter>
    </Card>
  )
}
