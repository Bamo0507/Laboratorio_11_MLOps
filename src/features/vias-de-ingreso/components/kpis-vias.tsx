import { Card } from "@/components/ui/card"
import { formatoIndice, formatoPorcentaje } from "@/features/shared/datos/formato"
import type { ViaId } from "@/features/shared/datos/types"

import type { BarraPais, CrecimientoVia } from "../hooks/use-vias-de-ingreso"

type Props = {
  rango: { inicio: number; fin: number }
  porcentajeAereo: number
  mayorCrecimiento: CrecimientoVia | null
  anioPost: number
  paisPrincipal: BarraPais | undefined
}

function Kpi({ etiqueta, valor, detalle }: { etiqueta: string; valor: React.ReactNode; detalle: React.ReactNode }) {
  return (
    <Card className="gap-2 px-5 py-5">
      <p className="text-sm text-muted-foreground">{etiqueta}</p>
      <p className="font-heading text-2xl leading-tight font-semibold text-foreground">{valor}</p>
      <p className="text-sm leading-snug text-muted-foreground">{detalle}</p>
    </Card>
  )
}

function Muestra({ via }: { via: ViaId }) {
  return (
    <span
      aria-hidden
      className="mr-2 inline-block size-3 rounded-full align-middle"
      style={{ backgroundColor: `var(--via-${via})` }}
    />
  )
}

function Cifra({ children }: { children: React.ReactNode }) {
  return <span className="font-data font-medium text-foreground">{children}</span>
}

export function KpisVias({ rango, porcentajeAereo, mayorCrecimiento, anioPost, paisPrincipal }: Props) {
  return (
    <section aria-label="Indicadores clave" className="grid gap-4 md:grid-cols-3">
      <Kpi
        etiqueta={`Llegadas por vía aérea en ${rango.fin}`}
        valor={<span className="font-data">{formatoPorcentaje(porcentajeAereo)}</span>}
        detalle="Del total de visitantes que ingresaron al país ese año"
      />
      <Kpi
        etiqueta={`Vía con mayor crecimiento, ${rango.inicio} a ${rango.fin}`}
        valor={
          mayorCrecimiento ? (
            <>
              <Muestra via={mayorCrecimiento.via} />
              {mayorCrecimiento.nombre}
            </>
          ) : (
            "Sin dato"
          )
        }
        detalle={
          mayorCrecimiento && (
            <>
              <Cifra>{formatoIndice(mayorCrecimiento.indice!)}</Cifra> visitantes en {rango.fin} por cada 100 de{" "}
              {rango.inicio}
            </>
          )
        }
      />
      <Kpi
        etiqueta={`País principal por vía aérea en ${anioPost}`}
        valor={paisPrincipal?.pais ?? "Sin dato"}
        detalle={
          paisPrincipal && (
            <>
              <Cifra>{formatoPorcentaje(paisPrincipal.porcentajePost)}</Cifra> de las llegadas aéreas (
              {formatoPorcentaje(paisPrincipal.porcentajePre)} en 2019)
            </>
          )
        }
      />
    </section>
  )
}
