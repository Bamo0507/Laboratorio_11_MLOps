import { Card } from "@/components/ui/card"
import { formatoPersonas } from "@/features/shared/datos/formato"
import type { ModeloId } from "@/features/shared/datos/types"

import type { Metrica } from "../types"

type Props = {
  nombreSerie: string
  nombreModelo: Record<ModeloId, string>
  mejor: Metrica
  peor: Metrica
  seleccionado: Metrica
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

function Cifra({ children }: { children: React.ReactNode }) {
  return <span className="font-data font-medium text-foreground">{children}</span>
}

const entero = new Intl.NumberFormat("es-GT", { maximumFractionDigits: 0 })

export function KpisPronosticos({ nombreSerie, nombreModelo, mejor, peor, seleccionado }: Props) {
  return (
    <section aria-label="Indicadores clave" className="grid gap-4 md:grid-cols-3">
      <Kpi
        etiqueta={`Modelo que menos se equivoca, ${nombreSerie.toLowerCase()}`}
        valor={nombreModelo[mejor.modelo]}
        detalle={
          <>
            Se equivoca en promedio un <Cifra>{entero.format(mejor.mape)} %</Cifra> respecto a lo que realmente llegó
          </>
        }
      />
      <Kpi
        etiqueta="Modelo seleccionado"
        valor={nombreModelo[seleccionado.modelo]}
        detalle={
          <>
            Error promedio de <Cifra>{entero.format(seleccionado.mape)} %</Cifra>, unas{" "}
            <Cifra>{formatoPersonas(seleccionado.mae)}</Cifra> personas por mes
          </>
        }
      />
      <Kpi
        etiqueta="Modelo que más se equivoca"
        valor={nombreModelo[peor.modelo]}
        detalle={
          <>
            Error promedio de <Cifra>{entero.format(peor.mape)} %</Cifra>:{" "}
            {(peor.mape / mejor.mape).toLocaleString("es-GT", { maximumFractionDigits: 1 })} veces el del mejor modelo
          </>
        }
      />
    </section>
  )
}
