import { TrendingDown, TrendingUp } from "lucide-react"

import { NOMBRE_CORTO_CONTINENTE } from "@/features/shared/datos/continentes"
import {
  formatoIndice,
  formatoPersonas,
  formatoPorcentaje,
  formatoPuntos,
  formatoVariacion,
} from "@/features/shared/datos/formato"
import type { ContinenteId } from "@/features/shared/datos/types"
import { Cifra, FilaKpis, Kpi, Muestra } from "@/features/shared/ui/kpi"

import { MARGEN_EMPATE, PESO_MINIMO_MERCADO, type Recuperacion } from "../hooks/use-mercados-de-origen"

type Props = {
  anio: number
  total: number
  variacion: number | null
  esParcial: boolean
  principal: { continente: ContinenteId; nombre: string; porcentaje: number }
  cambioPeso: number | null
  empatados: Recuperacion[]
  anioRecuperacion: number
}

function lista(nombres: string[]) {
  return nombres.length === 1 ? nombres[0] : `${nombres.slice(0, -1).join(", ")} y ${nombres.at(-1)}`
}

export function KpisMercados({
  anio,
  total,
  variacion,
  esParcial,
  principal,
  cambioPeso,
  empatados,
  anioRecuperacion,
}: Props) {
  const Tendencia = variacion !== null && variacion < 0 ? TrendingDown : TrendingUp
  const indices = empatados.map((r) => r.indice)

  return (
    <FilaKpis>
      <Kpi
        etiqueta={`Visitantes en ${anio}`}
        valor={<span className="font-data">{formatoPersonas(total)}</span>}
        detalle={
          esParcial ? (
            <p>Año parcial: solo enero a junio</p>
          ) : variacion === null ? (
            <p>Sin año anterior para comparar</p>
          ) : (
            <p className="inline-flex items-center gap-1.5">
              <Tendencia className="size-4 shrink-0 text-foreground" aria-hidden />
              <span>
                <Cifra>{formatoVariacion(variacion)}</Cifra> frente a {anio - 1}
              </span>
            </p>
          )
        }
      />
      <Kpi
        etiqueta={`Continente principal en ${anio}`}
        valor={
          <>
            <Muestra color={`var(--continente-${principal.continente})`} />
            {principal.nombre}
          </>
        }
        detalle={
          <p>
            Aportó el <Cifra>{formatoPorcentaje(principal.porcentaje)}</Cifra> de los visitantes
            {cambioPeso !== null && (
              <>
                {" "}
                (<Cifra>{formatoPuntos(cambioPeso)}</Cifra> frente a {anio - 1})
              </>
            )}
          </p>
        }
      />
      <Kpi
        etiqueta={`Mejor recuperación, 2019 a ${anioRecuperacion}`}
        valor={
          empatados.length === 1 ? (
            <>
              <Muestra color={`var(--continente-${empatados[0].continente})`} />
              {empatados[0].nombre}
            </>
          ) : (
            `Empate entre ${empatados.length} mercados`
          )
        }
        detalle={
          empatados.length === 1 ? (
            <p>
              <Cifra>{formatoIndice(empatados[0].indice)}</Cifra> visitantes por cada 100 de 2019 (mercados con más del{" "}
              {PESO_MINIMO_MERCADO} % del total)
            </p>
          ) : (
            <p>
              {lista(empatados.map((r) => NOMBRE_CORTO_CONTINENTE[r.continente]))}: entre{" "}
              <Cifra>{formatoIndice(Math.min(...indices))}</Cifra> y <Cifra>{formatoIndice(Math.max(...indices))}</Cifra>{" "}
              visitantes por cada 100 de 2019 (diferencias menores a {MARGEN_EMPATE} puntos)
            </p>
          )
        }
      />
    </FilaKpis>
  )
}
