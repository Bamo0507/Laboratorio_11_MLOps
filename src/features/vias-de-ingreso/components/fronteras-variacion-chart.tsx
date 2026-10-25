"use client"

import { Bar, BarChart, Cell, LabelList, ReferenceLine, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { formatoPersonas, formatoVariacion } from "@/features/shared/datos/formato"
import { NotaQuiebre, PieFuente } from "@/features/shared/ui/pie-fuente"
import type { ViaId } from "@/features/shared/datos/types"
import { UsoDirectivo } from "@/features/shared/ui/uso-directivo"

import { VOLUMEN_MINIMO_FRONTERA, type VariacionFrontera } from "../hooks/use-vias-de-ingreso"
import { NOMBRE_VIA } from "../vias"

type Props = {
  variaciones: VariacionFrontera[]
  via: ViaId
  rango: { inicio: number; fin: number }
}

const ALTO_FILA = 44
const CONFIG = { variacion: { label: "Variación" } }

export function FronterasVariacionChart({ variaciones, via, rango }: Props) {
  const nombreVia = NOMBRE_VIA[via].toLowerCase()
  // Dominio simétrico: el cero queda al centro y el largo de las barras es comparable en ambos lados.
  const extremo = Math.max(10, ...variaciones.map((v) => Math.abs(v.variacion))) * 1.1
  const relevantes = variaciones.filter((v) => !v.basePequena)
  const crecen = relevantes.filter((v) => v.variacion >= 0).length
  const pequenas = variaciones.length - relevantes.length

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">
            Variación por frontera, vía {nombreVia}, {rango.inicio} a {rango.fin}
          </h2>
        </CardTitle>
        <CardDescription className="max-w-[75ch] text-sm leading-relaxed">
          {variaciones.length === 0
            ? `No hay fronteras de la vía ${nombreVia} con registros suficientes en ${rango.inicio} y ${rango.fin}.`
            : relevantes.length === 1
              ? `${relevantes[0].frontera} concentra casi todas las llegadas por vía ${nombreVia}: ${relevantes[0].variacion >= 0 ? "recibió" : "perdió"} ${formatoVariacion(Math.abs(relevantes[0].variacion)).replace(/^[+−]/, "")} ${relevantes[0].variacion >= 0 ? "más" : "menos"} visitantes en ${rango.fin} que en ${rango.inicio}.`
              : `${crecen} de ${relevantes.length} fronteras con volumen relevante recibieron más visitantes en ${rango.fin} que en ${rango.inicio}.`}
          {pequenas > 0 && ` ${pequenas === 1 ? "Otra frontera aparece" : `Otras ${pequenas} aparecen`} en gris por tener una base pequeña.`}
        </CardDescription>
        <UsoDirectivo>ubicar los puntos de entrada que concentran el crecimiento o la caída, para planificar personal y servicios de atención en cada uno.</UsoDirectivo>
      </CardHeader>

      <CardContent className="px-6">
        {variaciones.length === 0 ? (
          <p className="rounded-lg bg-muted px-4 py-6 text-center text-sm text-muted-foreground">
            Sin datos para esta selección. Prueba con otra vía o con otro rango de años.
          </p>
        ) : (
          <ChartContainer
            config={CONFIG}
            className="aspect-auto w-full"
            style={{ height: variaciones.length * ALTO_FILA + 24 }}
            role="img"
            aria-label={variaciones.map((v) => `${v.frontera} ${formatoVariacion(v.variacion)}`).join(", ")}
          >
            <BarChart data={variaciones} layout="vertical" margin={{ top: 0, right: 72, bottom: 0, left: 0 }}>
              <XAxis type="number" domain={[-extremo, extremo]} hide />
              <YAxis
                type="category"
                dataKey="frontera"
                width={170}
                tickLine={false}
                axisLine={false}
                tick={({ x, y, payload }) => {
                  const v = variaciones.find((f) => f.frontera === payload.value)
                  return (
                    <text x={Number(x) - 8} y={Number(y)} dy={4} textAnchor="end" style={{ fontSize: 13 }}>
                      <tspan className="fill-foreground">{payload.value}</tspan>
                      {v?.basePequena && <tspan className="fill-muted-foreground" x={Number(x) - 8} dy={15} style={{ fontSize: 11 }}>base pequeña</tspan>}
                    </text>
                  )
                }}
              />
              <ReferenceLine x={0} stroke="var(--muted-foreground)" />
              <ChartTooltip
                cursor={{ fill: "var(--muted)" }}
                content={({ active, payload }) => {
                  const dato = payload?.[0]?.payload as VariacionFrontera | undefined
                  if (!active || !dato) return null
                  return (
                    <div className="rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                      <p className="font-medium">{dato.frontera}</p>
                      <p className="font-data text-muted-foreground">
                        {rango.inicio}: {formatoPersonas(dato.inicial)} · {rango.fin}: {formatoPersonas(dato.final)}
                      </p>
                      <p className="font-data text-foreground">{formatoVariacion(dato.variacion)}</p>
                      {dato.basePequena && (
                        <p className="text-xs text-muted-foreground">Base pequeña: el porcentaje se exagera.</p>
                      )}
                    </div>
                  )
                }}
              />
              <Bar dataKey="variacion" barSize={20} isAnimationActive={false}>
                {variaciones.map((v) => (
                  <Cell
                    key={v.frontera}
                    fill={
                      v.basePequena
                        ? "var(--contexto)"
                        : v.variacion >= 0
                          ? "var(--divergente-positivo)"
                          : "var(--divergente-negativo)"
                    }
                  />
                ))}
                <LabelList
                  dataKey="variacion"
                  content={({ x, y, width, height, index }) => {
                    const v = variaciones[index ?? 0]
                    const fin = Number(x) + Number(width)
                    const positivo = v.variacion >= 0
                    return (
                      <text
                        x={positivo ? fin + 8 : fin - 8}
                        y={Number(y) + Number(height) / 2}
                        dy={4}
                        textAnchor={positivo ? "start" : "end"}
                        className="fill-foreground font-data"
                        style={{ fontSize: 12 }}
                      >
                        {formatoVariacion(v.variacion)}
                      </text>
                    )
                  }}
                />
              </Bar>
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <p>
          <span className="font-medium" style={{ color: "var(--divergente-positivo)" }}>Azul</span>: la frontera creció.{" "}
          <span className="font-medium" style={{ color: "var(--divergente-negativo)" }}>Naranja</span>: la frontera cayó.
        </p>
        <p>
          <span className="font-medium text-foreground">Gris</span>: frontera con menos de{" "}
          {formatoPersonas(VOLUMEN_MINIMO_FRONTERA)} visitantes en {rango.inicio}; sobre bases tan pequeñas el porcentaje
          se exagera, así que se muestra solo como contexto.
        </p>
        <NotaQuiebre />
        <PieFuente />
      </CardFooter>
    </Card>
  )
}
