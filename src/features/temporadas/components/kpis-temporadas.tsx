import { formatoPorcentaje } from "@/features/shared/datos/formato"
import { Cifra, FilaKpis, Kpi } from "@/features/shared/ui/kpi"

import { MESES_LARGOS, type Extremos } from "../hooks/use-temporadas"

type PerfilPais = Extremos & { razon: number }

type Props = {
  etiquetaPeriodo: string
  etiquetaOtro: string
  actual: PerfilPais
  otro: PerfilPais
}

const decimal = new Intl.NumberFormat("es-GT", { maximumFractionDigits: 1, minimumFractionDigits: 1 })

export function KpisTemporadas({ etiquetaPeriodo, etiquetaOtro, actual, otro }: Props) {
  return (
    <FilaKpis>
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
    </FilaKpis>
  )
}
