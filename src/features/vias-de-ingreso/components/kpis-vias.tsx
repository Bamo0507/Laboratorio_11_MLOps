import { formatoIndice, formatoPorcentaje } from "@/features/shared/datos/formato"
import { Cifra, FilaKpis, Kpi, Muestra } from "@/features/shared/ui/kpi"

import { ANIO_PRE_PANDEMIA, type BarraPais, type CrecimientoVia } from "../hooks/use-vias-de-ingreso"

type Props = {
  rango: { inicio: number; fin: number }
  porcentajeAereo: number
  porcentajeAereoInicio: number
  mayorCrecimiento: CrecimientoVia | null
  anioPost: number
  paisPrincipal: BarraPais | undefined
}

export function KpisVias({ rango, porcentajeAereo, porcentajeAereoInicio, mayorCrecimiento, anioPost, paisPrincipal }: Props) {
  return (
    <FilaKpis>
      <Kpi
        etiqueta={`Llegadas por vía aérea en ${rango.fin}`}
        valor={<span className="font-data">{formatoPorcentaje(porcentajeAereo)}</span>}
        detalle={
          <p>
            Del total de visitantes de ese año (<Cifra>{formatoPorcentaje(porcentajeAereoInicio)}</Cifra> en{" "}
            {rango.inicio})
          </p>
        }
      />
      <Kpi
        etiqueta={`Vía con mayor crecimiento, ${rango.inicio} a ${rango.fin}`}
        valor={
          mayorCrecimiento ? (
            <>
              <Muestra color={`var(--via-${mayorCrecimiento.via})`} />
              {mayorCrecimiento.nombre}
            </>
          ) : (
            "Sin dato"
          )
        }
        detalle={
          mayorCrecimiento && (
            <p>
              <Cifra>{formatoIndice(mayorCrecimiento.indice!)}</Cifra> visitantes en {rango.fin} por cada 100 de{" "}
              {rango.inicio}
            </p>
          )
        }
      />
      <Kpi
        etiqueta={`País principal por vía aérea en ${anioPost}`}
        valor={paisPrincipal?.pais ?? "Sin dato"}
        detalle={
          paisPrincipal && (
            <p>
              <Cifra>{formatoPorcentaje(paisPrincipal.porcentajePost)}</Cifra> de las llegadas aéreas (
              {paisPrincipal.porcentajePre === null
                ? `sin dato en ${ANIO_PRE_PANDEMIA}`
                : `${formatoPorcentaje(paisPrincipal.porcentajePre)} en ${ANIO_PRE_PANDEMIA}`}
              )
            </p>
          )
        }
      />
    </FilaKpis>
  )
}
