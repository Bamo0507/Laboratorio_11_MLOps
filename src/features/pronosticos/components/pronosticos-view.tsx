"use client"

import { ChartNoAxesCombined, Info, RefreshCw, ShieldCheck } from "lucide-react"
import { useRouter } from "next/navigation"
import { useState, useTransition } from "react"
import { CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { formatoCompacto, formatoPersonas } from "@/features/shared/datos/formato"
import { FilaKpis, Kpi } from "@/features/shared/ui/kpi"

import { fechaPublicacion, mesCortoPublicado, mesPublicado } from "../formato-publicacion"
import type { EstadoPronosticos, PronosticoPublicado } from "../types"

const CONFIG = {
  observado: { label: "Valor observado en la base", color: "var(--observado)" },
  valor: { label: "Estimación aprobada", color: "var(--estimacion)" },
}

function ConsultarActualizacion() {
  const router = useRouter()
  const [pendiente, iniciar] = useTransition()
  return (
    <Button variant="outline" className="min-h-11" disabled={pendiente} onClick={() => iniciar(() => router.refresh())}>
      <RefreshCw data-icon="inline-start" />
      {pendiente ? "Consultando…" : "Consultar actualización"}
    </Button>
  )
}

function ResultadosAprobados({ datos }: { datos: PronosticoPublicado }) {
  const [vista, setVista] = useState("grafico")
  const periodo = `${mesPublicado(datos.periodo.inicio)} a ${mesPublicado(datos.periodo.fin)}`
  return (
    <>
      <section className="flex flex-wrap items-start justify-between gap-4" aria-label="Estado de los resultados">
        <div className="flex max-w-[75ch] flex-col gap-2">
          <p className="flex items-center gap-2 text-sm font-medium text-primary"><ShieldCheck className="size-4" aria-hidden />Versión aprobada</p>
          <p className="text-base leading-relaxed text-muted-foreground">Llegadas mensuales a {datos.destino}, sin residentes. Compara los valores reportados en la base con las estimaciones del período evaluado.</p>
        </div>
        <ConsultarActualizacion />
      </section>
      {datos.demostracion && (
        <Alert>
          <Info aria-hidden />
          <AlertTitle>Datos sintéticos de prueba</AlertTitle>
          <AlertDescription>Esta vista sirve para comprobar el tablero. No representa cifras de turismo ni una aprobación de los datos reales.</AlertDescription>
        </Alert>
      )}
      <FilaKpis>
        <Kpi etiqueta="Error promedio por mes · MAE" valor={`${formatoPersonas(datos.metricas.mae)} llegadas`} detalle={<p>Promedio de la diferencia absoluta entre lo estimado y lo observado.</p>} />
        <Kpi etiqueta="Error con mayor peso a diferencias grandes · RMSE" valor={`${formatoPersonas(datos.metricas.rmse)} llegadas`} detalle={<p>Un valor menor indica menos error. Evaluado sobre {datos.periodo.meses} meses.</p>} />
        <Kpi etiqueta="Última actualización" valor={<time dateTime={datos.fechaGeneracion}>{fechaPublicacion(datos.fechaGeneracion)}</time>} detalle={<p>Fecha de generación de los resultados que están aprobados para consulta.</p>} />
      </FilaKpis>
      <Card className="py-6">
        <CardHeader className="gap-3 px-6">
          <CardTitle><h2>Estimado y observado, mes a mes</h2></CardTitle>
          <CardDescription>Período de validación de {periodo}. Cantidades en llegadas por mes.</CardDescription>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap gap-4 text-sm" aria-label="Leyenda del gráfico">
              <span className="flex items-center gap-2"><span aria-hidden className="w-7 border-t-2 border-observado" />Observado en la base</span>
              <span className="flex items-center gap-2"><span aria-hidden className="w-7 border-t-2 border-dashed border-estimacion" />Estimación aprobada</span>
            </div>
            <ToggleGroup aria-label="Presentación de los resultados" value={[vista]} onValueChange={(v) => v[0] && setVista(v[0])} variant="outline" spacing={1}>
              <ToggleGroupItem className="min-h-11 cursor-pointer px-4" value="grafico">Gráfico</ToggleGroupItem>
              <ToggleGroupItem className="min-h-11 cursor-pointer px-4" value="tabla">Tabla</ToggleGroupItem>
            </ToggleGroup>
          </div>
        </CardHeader>
        <CardContent className="px-6">
          {vista === "grafico" ? (
            <ChartContainer config={CONFIG} className="h-80 w-full aspect-auto" aria-label={`Comparación de valores observados y estimaciones aprobadas de ${periodo}. La línea continua representa lo observado y la discontinua lo estimado.`}>
              <ComposedChart data={datos.estimaciones} accessibilityLayer margin={{ left: 0, right: 12, top: 20, bottom: 12 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="fecha" tickFormatter={mesCortoPublicado} tickLine={false} axisLine={false} minTickGap={20} />
                <YAxis tickFormatter={formatoCompacto} width={60} tickLine={false} axisLine={false} domain={[0, "auto"]} />
                <ChartTooltip content={<ChartTooltipContent labelFormatter={(label) => mesPublicado(String(label))} formatter={(valor, nombre) => <span>{nombre === "observado" ? "Observado en la base" : "Estimación aprobada"}<strong className="ml-3 font-data">{formatoPersonas(Number(valor))} llegadas</strong></span>} />} />
                <Line type="linear" dataKey="observado" stroke="var(--color-observado)" strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                <Line type="linear" dataKey="valor" stroke="var(--color-valor)" strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3 }} isAnimationActive={false} />
              </ComposedChart>
            </ChartContainer>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <caption className="sr-only">Valores observados y estimaciones aprobadas en llegadas por mes</caption>
                <thead><tr className="border-b text-left"><th scope="col" className="py-3 pr-3">Mes</th><th scope="col" className="py-3 pr-3 text-right">Observado en la base</th><th scope="col" className="py-3 text-right">Estimación aprobada</th></tr></thead>
                <tbody>{datos.estimaciones.map((fila) => <tr key={fila.fecha} className="border-b last:border-0"><th scope="row" className="py-3 pr-3 text-left font-normal">{mesPublicado(fila.fecha)}</th><td className="py-3 pr-3 text-right font-data">{formatoPersonas(fila.observado)}</td><td className="py-3 text-right font-data">{formatoPersonas(fila.valor)}</td></tr>)}</tbody>
              </table>
            </div>
          )}
        </CardContent>
        <CardFooter className="px-6 text-sm leading-relaxed text-muted-foreground">El error de validación corresponde a {periodo}. Cambiar entre gráfico y tabla no recalcula el modelo ni modifica estas métricas.</CardFooter>
      </Card>
      <Alert>
        <Info aria-hidden />
        <AlertTitle>Alcance de las estimaciones</AlertTitle>
        <AlertDescription>Las cifras son de uso académico y no son oficiales. Esta comparación utiliza meses con datos reportados en la base consolidada, por lo que no es una proyección de meses futuros. El error de este período no garantiza el desempeño posterior ni reproduce exactamente la información disponible en tiempo real.</AlertDescription>
      </Alert>
    </>
  )
}

export function PronosticosView({ estado }: { estado: EstadoPronosticos }) {
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      {estado.estado === "disponible" ? <ResultadosAprobados datos={estado.datos} key={estado.datos.fechaGeneracion} /> : (
        <>
          <p className="max-w-[70ch] text-base leading-relaxed text-muted-foreground">Consulta las estimaciones de llegadas a Guatemala que han completado la validación. Los resultados se actualizan cuando se aprueba una nueva versión.</p>
          <Card className="py-6">
            <Empty className="min-h-80">
              <EmptyHeader>
                <EmptyMedia variant="icon"><ChartNoAxesCombined aria-hidden /></EmptyMedia>
                <EmptyTitle><h2>{estado.motivo === "sin_version_aprobada" ? "Estimaciones no disponibles" : "Estimaciones temporalmente no disponibles"}</h2></EmptyTitle>
                <EmptyDescription>{estado.motivo === "sin_version_aprobada" ? "Todavía no hay una versión aprobada para consulta. Cuando haya resultados validados, aquí podrás ver las estimaciones y su error de validación." : "No pudimos verificar los resultados aprobados. Consulta de nuevo más tarde."}</EmptyDescription>
              </EmptyHeader>
              <EmptyContent><ConsultarActualizacion /></EmptyContent>
            </Empty>
            <CardFooter className="px-6 text-sm leading-relaxed text-muted-foreground">Una actualización que no supera los controles no reemplaza los resultados aprobados. Si existe una versión anterior, se conserva para consulta.</CardFooter>
          </Card>
        </>
      )}
    </div>
  )
}
