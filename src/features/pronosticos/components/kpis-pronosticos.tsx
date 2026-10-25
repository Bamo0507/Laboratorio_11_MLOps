import { formatoPersonas, formatoPorcentaje } from "@/features/shared/datos/formato"
import type { ModeloId } from "@/features/shared/datos/types"
import { Cifra, FilaKpis, Kpi } from "@/features/shared/ui/kpi"

import type { Metrica } from "../types"

type Props = {
  nombreSerie: string
  nombreModelo: Record<ModeloId, string>
  mejor: Metrica
  peor: Metrica
  seleccionado: Metrica
}

const decimal = new Intl.NumberFormat("es-GT", { maximumFractionDigits: 1 })

export function KpisPronosticos({ nombreSerie, nombreModelo, mejor, peor, seleccionado }: Props) {
  return (
    <FilaKpis>
      <Kpi
        etiqueta={`Modelo que menos se equivoca, ${nombreSerie.toLowerCase()}`}
        valor={nombreModelo[mejor.modelo]}
        detalle={
          <p>
            Se equivoca en promedio un <Cifra>{formatoPorcentaje(mejor.mape)}</Cifra> respecto a lo que realmente llegó
          </p>
        }
      />
      <Kpi
        etiqueta="Modelo seleccionado"
        valor={nombreModelo[seleccionado.modelo]}
        detalle={
          <p>
            Error promedio de <Cifra>{formatoPorcentaje(seleccionado.mape)}</Cifra>, unas{" "}
            <Cifra>{formatoPersonas(seleccionado.mae)}</Cifra> personas por mes
          </p>
        }
      />
      <Kpi
        etiqueta="Modelo que más se equivoca"
        valor={nombreModelo[peor.modelo]}
        detalle={
          <p>
            Error promedio de <Cifra>{formatoPorcentaje(peor.mape)}</Cifra>: {decimal.format(peor.mape / mejor.mape)} veces
            el del mejor modelo
          </p>
        }
      />
    </FilaKpis>
  )
}
