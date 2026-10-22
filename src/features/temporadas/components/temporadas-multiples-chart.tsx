"use client"

import { Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ReferenceLine, XAxis, YAxis } from "recharts"

import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { CHART_CONFIG_CONTINENTES, CONTINENTES } from "@/features/shared/datos/continentes"
import { formatoPorcentaje } from "@/features/shared/datos/formato"
import type { ContinenteId } from "@/features/shared/datos/types"

import {
  INICIALES_MESES,
  MES_PROMEDIO,
  MESES_LARGOS,
  PERIODOS,
  type PeriodoId,
  type PuntoPerfil,
  type ResumenContinente,
} from "../hooks/use-temporadas"

type Cambio = { continente: ContinenteId; nombre: string; mesOtro: number; mes: number }

type Props = {
  periodo: PeriodoId
  onCambiarPeriodo: (periodo: PeriodoId) => void
  otro: PeriodoId
  serie: PuntoPerfil[]
  resumen: ResumenContinente[]
  cambios: Cambio[]
  maximoY: number
  aniosPorPeriodo: Record<PeriodoId, number>
}

const ALTO_PANEL = 184
const MESES_TICKS = Array.from({ length: 12 }, (_, i) => i + 1)

function lista(nombres: string[]) {
  return nombres.length === 1 ? nombres[0] : `${nombres.slice(0, -1).join(", ")} y ${nombres.at(-1)}`
}

function hallazgo(resumen: ResumenContinente[], etiqueta: string) {
  const grupos = new Map<number, ResumenContinente[]>()
  for (const r of resumen) grupos.set(r.mesPico, [...(grupos.get(r.mesPico) ?? []), r])
  const ordenados = [...grupos.entries()].sort((a, b) => b[1].length - a[1].length)
  const [mesComun, grupo] = ordenados[0]
  const detalle = ordenados
    .slice(1)
    .map(([mes, rs]) => `; ${lista(rs.map((r) => r.nombre))} ${rs.length > 1 ? "llegan" : "llega"} más en ${MESES_LARGOS[mes - 1]}`)
    .join("")
  return `En promedio, entre ${etiqueta} ${MESES_LARGOS[mesComun - 1]} es el mes con más llegadas para ${grupo.length} de ${resumen.length} continentes${detalle}.`
}

function Panel({ r, serie, maximoY, mostrarEtiquetaPromedio }: { r: ResumenContinente; serie: PuntoPerfil[]; maximoY: number; mostrarEtiquetaPromedio: boolean }) {
  const id = r.continente
  const ticksY = Array.from({ length: maximoY / 5 + 1 }, (_, i) => i * 5)

  return (
    <figure className="flex flex-col gap-2 rounded-lg border p-4">
      <figcaption className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <span aria-hidden className="size-2.5 rounded-full" style={{ backgroundColor: `var(--continente-${id})` }} />
          {r.nombre}
        </span>
        <span className="text-sm text-muted-foreground">
          Pico:{" "}
          <span className="font-medium text-foreground">{MESES_LARGOS[r.mesPico - 1]}</span>
          {!r.picoClaro && (
            <span title={`Fue el mes más alto en ${r.aniosConPico} de ${r.anios} años`}> · varía según el año</span>
          )}
        </span>
      </figcaption>

      <ChartContainer
        config={CHART_CONFIG_CONTINENTES}
        className="aspect-auto w-full"
        style={{ height: ALTO_PANEL }}
        role="img"
        aria-label={`${r.nombre}: el mes con más llegadas es ${MESES_LARGOS[r.mesPico - 1]} (${formatoPorcentaje(r.porcentajePico)} del año)${r.picoClaro ? "" : `, aunque solo fue el más alto en ${r.aniosConPico} de ${r.anios} años`}; el de menos es ${MESES_LARGOS[r.mesBajo - 1]} (${formatoPorcentaje(r.porcentajeBajo)}).`}
      >
        <ComposedChart data={serie} margin={{ top: 20, right: 24, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis
            dataKey="mes"
            type="number"
            domain={[1, 12]}
            ticks={MESES_TICKS}
            interval={0}
            tickFormatter={(mes: number) => INICIALES_MESES[mes - 1]}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            domain={[0, maximoY]}
            ticks={ticksY}
            tickFormatter={(v: number) => `${v} %`}
            width={40}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 12 }}
          />
          <ReferenceLine
            y={MES_PROMEDIO}
            stroke="var(--muted-foreground)"
            strokeDasharray="4 4"
            label={
              mostrarEtiquetaPromedio
                ? { value: "reparto parejo 8.3 %", position: "insideBottomLeft", fontSize: 11, fill: "var(--muted-foreground)" }
                : undefined
            }
          />
          <ChartTooltip
            cursor={{ stroke: "var(--border)" }}
            content={({ active, payload }) => {
              const punto = payload?.[0]?.payload as PuntoPerfil | undefined
              if (!active || !punto) return null
              const [minimo, maximo] = punto[`${id}_rango`] as [number, number]
              return (
                <div className="rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                  <p className="font-medium first-letter:uppercase">{MESES_LARGOS[punto.mes - 1]}</p>
                  <p className="font-data text-foreground">{formatoPorcentaje(punto[id] as number)} en promedio</p>
                  <p className="font-data text-muted-foreground">
                    Entre {formatoPorcentaje(minimo)} y {formatoPorcentaje(maximo)} según el año
                  </p>
                </div>
              )
            }}
          />
          {/* Banda: mínimo y máximo entre años. Muestra cuánto se aleja cada año del promedio. */}
          <Area
            dataKey={`${id}_rango`}
            type="linear"
            fill={`var(--color-${id})`}
            fillOpacity={0.15}
            stroke="none"
            activeDot={false}
            isAnimationActive={false}
          />
          {/* Contexto: los demás continentes en gris, para comparar la forma sin cambiar de panel. */}
          {CONTINENTES.filter((otro) => otro !== id).map((otro) => (
            <Line
              key={otro}
              dataKey={otro}
              type="linear"
              stroke="var(--contexto)"
              strokeWidth={1}
              strokeOpacity={0.6}
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
          ))}
          <Line
            dataKey={id}
            type="linear"
            stroke={`var(--color-${id})`}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--card)" }}
            isAnimationActive={false}
          />
          <ReferenceDot
            x={r.mesPico}
            y={r.porcentajePico}
            r={4}
            fill={`var(--color-${id})`}
            stroke="var(--card)"
            strokeWidth={2}
            label={{
              value: formatoPorcentaje(r.porcentajePico),
              position: "top",
              offset: 8,
              fontSize: 12,
              fontWeight: 600,
              fill: "var(--foreground)",
            }}
          />
        </ComposedChart>
      </ChartContainer>

      <table className="sr-only">
        <caption>{r.nombre}: % de las llegadas del año por mes</caption>
        <tbody>
          {serie.map((p) => (
            <tr key={p.mes}>
              <th scope="row">{MESES_LARGOS[p.mes - 1]}</th>
              <td>{formatoPorcentaje(p[id] as number)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  )
}

export function TemporadasMultiplesChart({
  periodo,
  onCambiarPeriodo,
  otro,
  serie,
  resumen,
  cambios,
  maximoY,
  aniosPorPeriodo,
}: Props) {
  const etiqueta = PERIODOS[periodo].etiqueta

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">
            ¿En qué meses del año llegan más visitantes y cambia según el continente?
          </h2>
        </CardTitle>
        <CardDescription className="max-w-[80ch] text-sm leading-relaxed">{hallazgo(resumen, etiqueta)}</CardDescription>
        <CardAction>
          <ToggleGroup
            aria-label="Periodo"
            value={[periodo]}
            onValueChange={(valor) => valor[0] && onCambiarPeriodo(valor[0] as PeriodoId)}
            variant="outline"
            spacing={0}
          >
            {(Object.keys(PERIODOS) as PeriodoId[]).map((id) => (
              <ToggleGroupItem
                key={id}
                value={id}
                className="h-10 cursor-pointer px-3 text-sm transition-colors duration-150 hover:bg-muted hover:text-foreground data-pressed:bg-accent data-pressed:font-medium data-pressed:text-accent-foreground data-pressed:hover:bg-accent"
              >
                {PERIODOS[id].corta} ({PERIODOS[id].etiqueta})
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </CardAction>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 px-6">
        {cambios.length > 0 && (
          <p className="rounded-lg bg-muted px-4 py-3 text-sm leading-relaxed text-foreground">
            <span className="font-semibold">Cambio frente a {PERIODOS[otro].etiqueta}:</span>{" "}
            {cambios
              .map((c) =>
                periodo === "post"
                  ? `${c.nombre} pasó de ${MESES_LARGOS[c.mesOtro - 1]} a ${MESES_LARGOS[c.mes - 1]}`
                  : `${c.nombre} tenía su pico en ${MESES_LARGOS[c.mes - 1]} y después pasó a ${MESES_LARGOS[c.mesOtro - 1]}`
              )
              .join("; ")}
            .
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {CONTINENTES.map((id, i) => {
            const r = resumen.find((x) => x.continente === id)
            return r ? <Panel key={id} r={r} serie={serie} maximoY={maximoY} mostrarEtiquetaPromedio={i === 0} /> : null
          })}
        </div>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1.5 border-t px-6 pt-4 pb-5 text-sm leading-relaxed text-muted-foreground">
        <p>
          La línea es el % de las llegadas del año que cae en cada mes, promediado entre {aniosPorPeriodo[periodo]} años
          ({etiqueta}); la franja de color muestra el año más bajo y el más alto. La línea punteada marca{" "}
          {formatoPorcentaje(MES_PROMEDIO)}, lo que recibiría cada mes si las llegadas se repartieran parejo: por encima
          es temporada alta.
        </p>
        <p>
          &quot;Varía según el año&quot; indica que ese mes fue el más alto en la mitad de los años o menos: el promedio
          lo marca como pico, pero no se repite de forma constante. Todos los paneles usan el mismo eje en ambos periodos. No se ajusta por días del mes: febrero tiene hasta 3 días menos.
        </p>
        <p>
          Se excluyen 2020 (abril a agosto sin dato) y 2021, año de transición, para comparar años completos y
          comparables. Fuente: Base de Migración, turistas y excursionistas. Datos hasta junio de 2026.
        </p>
      </CardFooter>
    </Card>
  )
}
