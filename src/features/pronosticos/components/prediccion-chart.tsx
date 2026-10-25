"use client"

import { Area, Brush, CartesianGrid, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, type ChartConfig } from "@/components/ui/chart"
import { formatoCompacto, formatoPersonas, formatoPorcentaje } from "@/features/shared/datos/formato"
import type { SerieId } from "@/features/shared/datos/types"
import { PieFuente } from "@/features/shared/ui/pie-fuente"
import { UsoDirectivo } from "@/features/shared/ui/uso-directivo"

import type { PuntoPronostico } from "../hooks/use-pronosticos"

type Props = {
  puntos: PuntoPronostico[]
  serie: SerieId
  nombreModelo: string
  finEntrenamiento: string
  quiebre: string
  bandaPorMae: boolean
  mae: number
  cobertura: number | null
  rango: { inicio: number; fin: number } | null
  onCambiarRango: (rango: { inicio: number; fin: number }) => void
}

const ALTO_GRAFICO = 380
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

export function etiquetaMes(fecha: string) {
  const [anio, mes] = fecha.split("-")
  return `${MESES[Number(mes) - 1]} ${anio}`
}

const CONFIG = {
  real: { label: "Observado", color: "var(--observado)" },
  prediccion: { label: "Estimado", color: "var(--estimacion)" },
  banda: { label: "Franja", color: "var(--estimacion)" },
} satisfies ChartConfig

export function PrediccionChart({
  puntos,
  serie,
  nombreModelo,
  finEntrenamiento,
  quiebre,
  bandaPorMae,
  mae,
  cobertura,
  rango,
  onCambiarRango,
}: Props) {
  const nombreBanda = bandaPorMae ? "Rango típico de error (± MAE)" : "Banda de incertidumbre (95 %, calculada para el tablero)"
  const prueba = puntos.filter((p) => p.prediccion !== null)
  const debajo = prueba.filter((p) => p.prediccion! < p.real).length
  // El eje se ajusta a lo observado y lo estimado; la banda puede crecer tanto que aplasta las líneas, así que se recorta.
  const maximo = Math.max(1, ...puntos.map((p) => Math.max(p.real, p.prediccion ?? 0)))
  let paso = 10 ** Math.floor(Math.log10(maximo))
  if (maximo / paso < 3) paso /= 2
  const techo = Math.ceil(maximo / paso) * paso
  const ticksY = Array.from({ length: techo / paso + 1 }, (_, i) => i * paso)
  const bandaRecortada = !bandaPorMae && puntos.some((p) => p.banda && p.banda[1] > techo)
  const ticksX = puntos.filter((p) => p.fecha.endsWith("-01")).map((p) => p.fecha)

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">
            ¿Qué tan confiables son los pronósticos de llegadas?
          </h2>
        </CardTitle>
        <CardDescription className="max-w-[75ch] text-sm leading-relaxed">
          Línea continua: lo que realmente llegó; punteada: lo que estimó {nombreModelo}. Quedó por debajo de lo observado
          en {debajo} de {prueba.length} meses del periodo de prueba.
        </CardDescription>
        <UsoDirectivo>comprobar si un pronóstico es confiable para planificar. Si lo observado se sale seguido de la franja, la estimación debe usarse con cautela.</UsoDirectivo>
      </CardHeader>

      <CardContent className="flex flex-col gap-3 px-6">
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-2">
            <span aria-hidden className="h-0.5 w-5" style={{ backgroundColor: "var(--observado)" }} />
            Observado
          </span>
          <span className="flex items-center gap-2">
            <span aria-hidden className="w-5 border-t-2 border-dashed" style={{ borderColor: "var(--estimacion)" }} />
            Estimado ({nombreModelo})
          </span>
          <span className="flex items-center gap-2">
            <span aria-hidden className="h-3 w-5 rounded-sm opacity-20" style={{ backgroundColor: "var(--estimacion)" }} />
            {nombreBanda}
          </span>
        </div>

        <p className="rounded-lg bg-muted px-4 py-3 text-sm leading-relaxed text-foreground">
          {bandaPorMae ? (
            <>
              La red LSTM no genera una banda de incertidumbre. La franja muestra ± su error promedio en la prueba (
              <span className="font-data">{formatoPersonas(mae)}</span> personas) como referencia de qué tan lejos suele
              quedar el dato real.
            </>
          ) : (
            "La banda no viene de los laboratorios: se calculó para el tablero con el mismo modelo."
          )}
          {cobertura !== null && (
            <>
              {" "}
              Lo observado cayó dentro de la franja en <span className="font-data font-semibold">{formatoPorcentaje(cobertura)}</span>{" "}
              de los meses de prueba.
            </>
          )}
        </p>

        <p className="text-xs font-medium text-muted-foreground">Viajeros por mes</p>

        <ChartContainer
          config={CONFIG}
          className="-mt-2 aspect-auto w-full"
          style={{ height: ALTO_GRAFICO }}
          role="img"
          aria-label={`Llegadas observadas contra la estimación de ${nombreModelo}. El modelo quedó por debajo en ${debajo} de ${prueba.length} meses.`}
        >
          {/* key: al cambiar de serie cambia el número de meses y el Brush conservaría la escala anterior (NaN). */}
          <ComposedChart key={serie} data={puntos} margin={{ top: 16, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis
              dataKey="fecha"
              ticks={ticksX}
              tickFormatter={(fecha: string) => fecha.slice(0, 4)}
              interval={0}
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              domain={[0, techo]}
              ticks={ticksY}
              allowDataOverflow
              tickFormatter={formatoCompacto}
              width={56} tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
            {serie === "total" && (
              <ReferenceLine
                x={finEntrenamiento}
                stroke="var(--muted-foreground)"
                strokeDasharray="4 4"
                label={{ value: "Fin del entrenamiento", position: "insideTopRight", fill: "var(--muted-foreground)", fontSize: 12 }}
              />
            )}
            <ReferenceLine
              x={quiebre}
              stroke="var(--muted-foreground)"
              strokeDasharray="2 3"
              label={{ value: "Sin residentes desde aquí", position: "insideTopLeft", fill: "var(--muted-foreground)", fontSize: 12 }}
            />
            <ChartTooltip
              content={({ active, payload, label }) => {
                const p = payload?.[0]?.payload as PuntoPronostico | undefined
                if (!active || !p) return null
                return (
                  <div className="min-w-52 rounded-lg border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
                    <p className="mb-1 font-medium">{etiquetaMes(String(label))}</p>
                    <p className="flex justify-between gap-4">
                      Observado <span className="font-data">{formatoPersonas(p.real)}</span>
                    </p>
                    {p.prediccion !== null && (
                      <p className="flex justify-between gap-4" style={{ color: "var(--estimacion)" }}>
                        Estimado <span className="font-data">{formatoPersonas(p.prediccion)}</span>
                      </p>
                    )}
                    {p.banda && p.prediccion !== null && (
                      <p className="font-data text-xs text-muted-foreground">
                        {bandaPorMae ? "Rango típico" : "Banda"}: {formatoPersonas(p.banda[0])} a {formatoPersonas(p.banda[1])}
                      </p>
                    )}
                  </div>
                )
              }}
            />
            <Area
              dataKey="banda"
              stroke="none"
              fill="var(--color-banda)"
              fillOpacity={0.15}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line dataKey="real" stroke="var(--color-real)" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line
              dataKey="prediccion"
              stroke="var(--color-prediccion)"
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Brush
              dataKey="fecha"
              height={28}
              travellerWidth={10}
              stroke="var(--muted-foreground)"
              fill="var(--card)"
              tickFormatter={etiquetaMes}
              startIndex={rango?.inicio ?? 0}
              endIndex={rango?.fin ?? puntos.length - 1}
              onChange={({ startIndex, endIndex }) =>
                startIndex !== undefined && endIndex !== undefined && onCambiarRango({ inicio: startIndex, fin: endIndex })
              }
            />
          </ComposedChart>
        </ChartContainer>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <p>Arrastra los extremos de la barra inferior para acotar el periodo: el gráfico de errores de abajo se ajusta.</p>
        <p>
          Los modelos solo vieron datos hasta {etiquetaMes(finEntrenamiento)}, en plena pandemia, y se evaluaron de{" "}
          {etiquetaMes(prueba[0]?.fecha ?? finEntrenamiento)} a {etiquetaMes(prueba.at(-1)?.fecha ?? finEntrenamiento)}: no
          conocieron la reapertura, así que su error mide sobre todo qué tan bien anticiparon una recuperación que no
          habían visto.
          {serie === "aurora" && " Para La Aurora solo se muestra el periodo de prueba."}
        </p>
        <p>
          Desde {etiquetaMes(quiebre)} la base deja de registrar a los residentes en Guatemala. Estas series los incluyen
          hasta 2022, igual que en los laboratorios, así que lo observado desde 2023 no es del todo comparable con los años
          anteriores.
        </p>
        {bandaRecortada && (
          <p>
            La banda de incertidumbre se recorta en la parte superior: crece tanto con los meses que, a largo plazo, el
            modelo admite casi cualquier valor.
          </p>
        )}
        <PieFuente extra="Predicciones: laboratorios 1 y 2." />
      </CardFooter>
    </Card>
  )
}
