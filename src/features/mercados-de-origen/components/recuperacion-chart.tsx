"use client"

import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceDot, ReferenceLine, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  CHART_CONFIG_CONTINENTES,
  CONTINENTES,
  NOMBRE_CONTINENTE,
  NOMBRE_CORTO_CONTINENTE,
} from "@/features/shared/datos/continentes"
import { formatoIndice, formatoPersonas, formatoPorcentaje } from "@/features/shared/datos/formato"
import type { ContinenteId } from "@/features/shared/datos/types"

import { PESO_MINIMO_MERCADO, type PuntoRecuperacion, type Recuperacion } from "../hooks/use-mercados-de-origen"

type Props = {
  serie: PuntoRecuperacion[]
  recuperacionFinal: Recuperacion[]
  mercadoPrincipal: Recuperacion
  ultimoAnio: number
  continenteResaltado: ContinenteId
  onSeleccionarContinente: (continente: ContinenteId) => void
}

const ALTO_GRAFICO = 380
// Separación mínima entre etiquetas finales, en unidades del índice.
const SEPARACION_ETIQUETAS = 11

function descripcion(r: Recuperacion, anio: number) {
  const base = `En ${anio}, ${r.nombre} recibió ${formatoIndice(r.indice)} visitantes por cada 100 que tuvo en 2019`
  if (r.basePequena) {
    return `${base}, pero sobre una base pequeña: pasó de ${formatoPersonas(r.viajeros2019)} a ${formatoPersonas(r.viajeros)} visitantes.`
  }
  return r.indice >= 100 ? `${base}: ya superó su nivel previo a la pandemia.` : `${base}: todavía no recupera su nivel previo a la pandemia.`
}

/** Reparte las etiquetas del final de las líneas para que no se encimen. */
function posicionesEtiquetas(final: Recuperacion[]) {
  const ordenadas = [...final].sort((a, b) => b.indice - a.indice)
  const posiciones = new Map<ContinenteId, number>()
  let anterior = Infinity
  for (const r of ordenadas) {
    const y = Math.min(r.indice, anterior - SEPARACION_ETIQUETAS)
    posiciones.set(r.continente, y)
    anterior = y
  }
  return posiciones
}

export function RecuperacionChart({
  serie,
  recuperacionFinal,
  mercadoPrincipal,
  ultimoAnio,
  continenteResaltado,
  onSeleccionarContinente,
}: Props) {
  const resaltado = recuperacionFinal.find((r) => r.continente === continenteResaltado) ?? recuperacionFinal[0]
  // Las líneas en gris se dibujan primero para que la resaltada quede encima.
  const orden = [...CONTINENTES.filter((id) => id !== continenteResaltado), continenteResaltado]
  const maximo = Math.max(...serie.flatMap((p) => CONTINENTES.map((id) => p[id] ?? 0)))
  const techo = Math.ceil(maximo / 50) * 50
  const ticksY = Array.from({ length: techo / 50 + 1 }, (_, i) => i * 50)
  const etiquetas = posicionesEtiquetas(recuperacionFinal)

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">
            Tras la pandemia, ¿qué continente ha mostrado la mejor recuperación?
          </h2>
        </CardTitle>
        <CardDescription className="max-w-[75ch] text-sm leading-relaxed">
          {descripcion(resaltado, ultimoAnio)}
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 px-6">
        {mercadoPrincipal.indice < 100 && (
          <p className="rounded-lg bg-muted px-4 py-3 text-sm leading-relaxed text-foreground">
            <span className="font-semibold">Dato clave:</span> {mercadoPrincipal.nombre}, el mercado más grande (
            {formatoPorcentaje(mercadoPrincipal.peso2019)} de los visitantes en 2019), sigue en{" "}
            <span className="font-data font-semibold">{formatoIndice(mercadoPrincipal.indice)}</span>: todavía está por
            debajo de su nivel de 2019.
          </p>
        )}

        <ToggleGroup
          aria-label="Continente a resaltar"
          value={[continenteResaltado]}
          onValueChange={(valor) => valor[0] && onSeleccionarContinente(valor[0] as ContinenteId)}
          variant="outline"
          spacing={2}
          className="flex-wrap"
        >
          {CONTINENTES.map((id) => (
            <ToggleGroupItem
              key={id}
              value={id}
              className="h-10 cursor-pointer gap-2 px-3 text-sm transition-colors duration-150 hover:border-foreground/30 hover:bg-muted hover:text-foreground data-pressed:border-primary data-pressed:bg-accent data-pressed:font-medium data-pressed:text-accent-foreground data-pressed:hover:bg-accent"
            >
              <span aria-hidden className="size-2.5 rounded-full" style={{ backgroundColor: `var(--continente-${id})` }} />
              {NOMBRE_CONTINENTE[id]}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>

        <p className="text-xs font-medium text-muted-foreground">Índice (2019 = 100)</p>

        <ChartContainer
          config={CHART_CONFIG_CONTINENTES}
          className="-mt-2 aspect-auto w-full"
          style={{ height: ALTO_GRAFICO }}
          role="img"
          aria-label={`${descripcion(resaltado, ultimoAnio)} ${mercadoPrincipal.nombre}, el mercado más grande, está en ${formatoIndice(mercadoPrincipal.indice)}.`}
        >
          <LineChart data={serie} margin={{ top: 12, right: 132, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <ReferenceArea
              x1={2020}
              x2={2021}
              fill="var(--muted)"
              fillOpacity={1}
              label={{ value: "Pandemia", position: "insideTop", fill: "var(--muted-foreground)", fontSize: 12 }}
            />
            <XAxis
              dataKey="anio"
              type="number"
              domain={["dataMin", "dataMax"]}
              ticks={serie.filter((p) => p.anio % 2 === 1).map((p) => p.anio)}
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
              label={{ value: "Nivel de 2019", position: "insideTopLeft", fill: "var(--muted-foreground)", fontSize: 12 }}
            />
            <ChartTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null
                const filas = [...payload].sort((a, b) => Number(b.value) - Number(a.value))
                return (
                  <div className="min-w-56 rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                    <p className="mb-1 font-medium">{label}</p>
                    {filas.map((fila) => {
                      const id = fila.dataKey as ContinenteId
                      return (
                        <p
                          key={id}
                          className={`flex items-center justify-between gap-4 ${id === continenteResaltado ? "font-medium text-foreground" : "text-muted-foreground"}`}
                        >
                          <span className="flex items-center gap-2">
                            <span aria-hidden className="size-2 rounded-full" style={{ backgroundColor: `var(--continente-${id})` }} />
                            {NOMBRE_CONTINENTE[id]}
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
              const activo = id === continenteResaltado
              return (
                <Line
                  key={id}
                  dataKey={id}
                  type="linear"
                  stroke={activo ? `var(--color-${id})` : "var(--contexto)"}
                  strokeWidth={activo ? 2.5 : 1.5}
                  dot={false}
                  activeDot={activo ? { r: 5, strokeWidth: 2, stroke: "var(--card)" } : false}
                  isAnimationActive={false}
                />
              )
            })}
            {/* Etiquetas directas al final de cada línea: el mensaje se lee sin pasar el cursor. */}
            {recuperacionFinal.map((r) => {
              const activo = r.continente === continenteResaltado
              return (
                <ReferenceDot
                  key={`etiqueta-${r.continente}`}
                  x={ultimoAnio}
                  y={etiquetas.get(r.continente) ?? r.indice}
                  r={0}
                  ifOverflow="visible"
                  label={{
                    value: `${NOMBRE_CORTO_CONTINENTE[r.continente]} ${formatoIndice(r.indice)}`,
                    position: "right",
                    offset: 10,
                    fontSize: activo ? 13 : 12,
                    fontWeight: activo ? 600 : 400,
                    fill: activo ? "var(--foreground)" : "var(--muted-foreground)",
                  }}
                />
              )
            })}
            <ReferenceDot
              x={ultimoAnio}
              y={resaltado.indice}
              r={5}
              fill={`var(--color-${resaltado.continente})`}
              stroke="var(--card)"
              strokeWidth={2}
            />
          </LineChart>
        </ChartContainer>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <p>
          Índice = visitantes del año ÷ visitantes de 2019 × 100. Un valor de 100 significa que el continente volvió a su
          nivel previo a la pandemia. {ultimoAnio + 1} no se incluye porque solo tiene datos de enero a junio.
        </p>
        <p>
          Asia y el resto del mundo representaban menos del {PESO_MINIMO_MERCADO} % de los visitantes en 2019: sobre
          bases tan pequeñas, sus variaciones se ven más grandes.
        </p>
        <p>Fuente: Base de Migración, turistas y excursionistas. Datos hasta junio de 2026.</p>
      </CardFooter>
    </Card>
  )
}
