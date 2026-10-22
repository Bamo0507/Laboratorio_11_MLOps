import { Card } from "@/components/ui/card"
import { formatoPorcentaje } from "@/features/shared/datos/formato"

import { MESES_LARGOS, type Extremos } from "../hooks/use-temporadas"

type PerfilPais = Extremos & { razon: number }

type Props = {
  etiquetaPeriodo: string
  etiquetaOtro: string
  actual: PerfilPais
  otro: PerfilPais
}

function Kpi({ etiqueta, valor, detalle }: { etiqueta: string; valor: React.ReactNode; detalle: React.ReactNode }) {
  return (
    <Card className="gap-2 px-5 py-5">
      <p className="text-sm text-muted-foreground">{etiqueta}</p>
      <p className="font-heading text-2xl leading-tight font-semibold text-foreground first-letter:uppercase">{valor}</p>
      <div className="flex flex-col gap-0.5 text-sm leading-snug text-muted-foreground">{detalle}</div>
    </Card>
  )
}

function Cifra({ children }: { children: React.ReactNode }) {
  return <span className="font-data font-medium text-foreground">{children}</span>
}

const decimal = new Intl.NumberFormat("es-GT", { maximumFractionDigits: 1, minimumFractionDigits: 1 })

export function KpisTemporadas({ etiquetaPeriodo, etiquetaOtro, actual, otro }: Props) {
  return (
    <section aria-label="Indicadores clave" className="grid gap-4 md:grid-cols-3">
      <Kpi
        etiqueta={`Mes con más llegadas, ${etiquetaPeriodo}`}
        valor={MESES_LARGOS[actual.mesPico - 1]}
        detalle={
          <>
            <p>
              Recibe en promedio el <Cifra>{formatoPorcentaje(actual.porcentajePico)}</Cifra> de las llegadas del año
            </p>
            <p>
              {etiquetaOtro}: {MESES_LARGOS[otro.mesPico - 1]}, {formatoPorcentaje(otro.porcentajePico)}
            </p>
          </>
        }
      />
      <Kpi
        etiqueta={`Mes con menos llegadas, ${etiquetaPeriodo}`}
        valor={MESES_LARGOS[actual.mesBajo - 1]}
        detalle={
          <>
            <p>
              Recibe en promedio el <Cifra>{formatoPorcentaje(actual.porcentajeBajo)}</Cifra> de las llegadas del año
            </p>
            <p>
              {etiquetaOtro}: {MESES_LARGOS[otro.mesBajo - 1]}, {formatoPorcentaje(otro.porcentajeBajo)}
            </p>
          </>
        }
      />
      <Kpi
        etiqueta="Temporada alta frente a baja"
        valor={
          <>
            <span className="font-data">{decimal.format(actual.razon)}</span> veces
          </>
        }
        detalle={
          <>
            <p className="first-letter:uppercase">
              {MESES_LARGOS[actual.mesPico - 1]} recibe en promedio {decimal.format(actual.razon)} veces las llegadas de{" "}
              {MESES_LARGOS[actual.mesBajo - 1]}
            </p>
            <p>
              {etiquetaOtro}: {decimal.format(otro.razon)} veces
            </p>
          </>
        }
      />
    </section>
  )
}
