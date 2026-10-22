import { TrendingDown, TrendingUp } from "lucide-react"

import { Card } from "@/components/ui/card"
import {
  formatoIndice,
  formatoPersonas,
  formatoPorcentaje,
  formatoPuntos,
  formatoVariacion,
} from "@/features/shared/datos/formato"
import type { ContinenteId } from "@/features/shared/datos/types"

import { PESO_MINIMO_MERCADO, type Recuperacion } from "../hooks/use-mercados-de-origen"

type Props = {
  anio: number
  total: number
  variacion: number | null
  esParcial: boolean
  principal: { continente: ContinenteId; nombre: string; porcentaje: number }
  cambioPeso: number | null
  recuperacion: Recuperacion
  anioRecuperacion: number
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

function Muestra({ continente }: { continente: ContinenteId }) {
  return (
    <span
      aria-hidden
      className="mr-2 inline-block size-3 rounded-full align-middle"
      style={{ backgroundColor: `var(--continente-${continente})` }}
    />
  )
}

function Cifra({ children }: { children: React.ReactNode }) {
  return <span className="font-data font-medium text-foreground">{children}</span>
}

export function KpisMercados({
  anio,
  total,
  variacion,
  esParcial,
  principal,
  cambioPeso,
  recuperacion,
  anioRecuperacion,
}: Props) {
  const Tendencia = variacion !== null && variacion < 0 ? TrendingDown : TrendingUp

  return (
    <section aria-label="Indicadores clave" className="grid gap-4 md:grid-cols-3">
      <Kpi
        etiqueta={`Visitantes en ${anio}`}
        valor={<span className="font-data">{formatoPersonas(total)}</span>}
        detalle={
          esParcial ? (
            "Año parcial: solo enero a junio"
          ) : variacion === null ? (
            "Sin año anterior para comparar"
          ) : (
            <span className="inline-flex items-center gap-1.5">
              <Tendencia className="size-4 shrink-0 text-foreground" aria-hidden />
              <span>
                <Cifra>{formatoVariacion(variacion)}</Cifra> frente a {anio - 1}
              </span>
            </span>
          )
        }
      />
      <Kpi
        etiqueta={`Continente principal en ${anio}`}
        valor={
          <>
            <Muestra continente={principal.continente} />
            {principal.nombre}
          </>
        }
        detalle={
          <>
            Aportó el <Cifra>{formatoPorcentaje(principal.porcentaje)}</Cifra> de los visitantes
            {cambioPeso !== null && (
              <>
                {" "}
                (<Cifra>{formatoPuntos(cambioPeso)}</Cifra> frente a {anio - 1})
              </>
            )}
          </>
        }
      />
      <Kpi
        etiqueta={`Mejor recuperación, 2019 a ${anioRecuperacion}`}
        valor={
          <>
            <Muestra continente={recuperacion.continente} />
            {recuperacion.nombre}
          </>
        }
        detalle={
          <>
            <Cifra>{formatoIndice(recuperacion.indice)}</Cifra> visitantes por cada 100 de 2019. Entre mercados con más
            del {PESO_MINIMO_MERCADO} % del total.
          </>
        }
      />
    </section>
  )
}
