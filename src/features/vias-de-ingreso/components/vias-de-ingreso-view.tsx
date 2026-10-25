"use client"

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

import { useViasDeIngreso, type Datos } from "../hooks/use-vias-de-ingreso"
import { CrecimientoViasChart } from "./crecimiento-vias-chart"
import { FronterasVariacionChart } from "./fronteras-variacion-chart"
import { KpisVias } from "./kpis-vias"
import { PaisesAereosChart } from "./paises-aereos-chart"

function SelectorAnio({
  etiqueta,
  anios,
  valor,
  onCambiar,
}: {
  etiqueta: string
  anios: number[]
  valor: number
  onCambiar: (anio: number) => void
}) {
  const items = anios.map((a) => ({ value: String(a), label: String(a) }))
  return (
    <label className="flex items-center gap-2 text-sm text-muted-foreground">
      {etiqueta}
      <Select items={items} value={String(valor)} onValueChange={(v) => v && onCambiar(Number(v))}>
        <SelectTrigger className="h-10 min-w-24 bg-card text-foreground" aria-label={etiqueta}>
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
  )
}

export function ViasDeIngresoView({ datos }: { datos: Datos }) {
  const v = useViasDeIngreso(datos)

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <p className="max-w-[70ch] text-base leading-relaxed text-muted-foreground">
        Por dónde entran los visitantes internacionales a Guatemala y cómo ha crecido cada vía. Elige un rango de años
        para comparar las vías, haz clic en una para ver el detalle por frontera y compara los países que más llegan
        por aire antes y después de la pandemia.
      </p>

      <KpisVias
        rango={v.rango}
        porcentajeAereo={v.kpis.porcentajeAereo}
        mayorCrecimiento={v.mayorCrecimiento}
        anioPost={v.anioPost}
        paisPrincipal={v.kpis.paisPrincipal}
      />

      <div className="flex flex-wrap items-center gap-4" role="group" aria-label="Rango de años">
        <span className="text-sm font-medium text-foreground">Rango de años</span>
        <SelectorAnio etiqueta="Desde" anios={v.anios.slice(0, -1)} valor={v.rango.inicio} onCambiar={v.cambiarInicio} />
        <SelectorAnio etiqueta="Hasta" anios={v.anios.slice(1)} valor={v.rango.fin} onCambiar={v.cambiarFin} />
      </div>

      <CrecimientoViasChart
        serie={v.serie}
        crecimientoFinal={v.crecimientoFinal}
        rango={v.rango}
        anioParcial={v.anioParcial}
        viaSeleccionada={v.viaSeleccionada}
        onSeleccionarVia={v.setViaSeleccionada}
      />

      <FronterasVariacionChart variaciones={v.variacionFronteras} via={v.viaSeleccionada} rango={v.rango} />

      <PaisesAereosChart barras={v.barrasPaises} anioPost={v.anioPost} onCambiarAnio={v.setAnioPost} />
    </div>
  )
}
