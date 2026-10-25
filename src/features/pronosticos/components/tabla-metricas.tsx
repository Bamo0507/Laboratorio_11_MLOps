import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { formatoPersonas, formatoPorcentaje } from "@/features/shared/datos/formato"
import type { ModeloId } from "@/features/shared/datos/types"
import { PieFuente } from "@/features/shared/ui/pie-fuente"

import type { Metrica } from "../types"

type Props = {
  metricas: Metrica[]
  nombreModelo: Record<ModeloId, string>
  modeloSeleccionado: ModeloId
}

export function TablaMetricas({ metricas, nombreModelo, modeloSeleccionado }: Props) {
  const mejor = metricas[0]?.modelo

  return (
    <Card className="gap-5 py-6">
      <CardHeader className="px-6">
        <CardTitle>
          <h2 className="font-heading text-lg font-semibold text-foreground">Comparación de los tres modelos</h2>
        </CardTitle>
        <CardDescription className="text-sm leading-relaxed">
          En las tres medidas, un número más bajo significa que el modelo se equivoca menos. Ordenado de mejor a peor.
        </CardDescription>
      </CardHeader>

      <CardContent className="flex flex-col gap-4 px-6">
        <div className="overflow-x-auto">
          <table className="w-full min-w-md text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th scope="col" className="py-2 pr-4 font-medium">Modelo</th>
                <th scope="col" className="py-2 pr-4 text-right font-medium">MAE</th>
                <th scope="col" className="py-2 pr-4 text-right font-medium">RMSE</th>
                <th scope="col" className="py-2 text-right font-medium">MAPE</th>
              </tr>
            </thead>
            <tbody className="font-data tabular-nums">
              {metricas.map((m) => (
                <tr
                  key={m.modelo}
                  className={`border-b last:border-0 ${m.modelo === modeloSeleccionado ? "bg-muted" : ""} ${m.modelo === mejor ? "font-semibold text-foreground" : "text-muted-foreground"}`}
                >
                  <th scope="row" className="py-2 pr-4 text-left font-sans">
                    {nombreModelo[m.modelo]}
                    {m.modelo === mejor && <span className="ml-2 text-xs font-normal">(menor error)</span>}
                  </th>
                  <td className="py-2 pr-4 text-right">{formatoPersonas(m.mae)}</td>
                  <td className="py-2 pr-4 text-right">{formatoPersonas(m.rmse)}</td>
                  <td className="py-2 text-right">{formatoPorcentaje(m.mape)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <dl className="grid gap-2 text-xs leading-relaxed text-muted-foreground md:grid-cols-3">
          <div>
            <dt className="font-medium text-foreground">Suavizamiento exponencial simple</dt>
            <dd>Pronostica con un promedio que pesa más los meses recientes. Da un valor plano hacia adelante.</dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">SARIMA</dt>
            <dd>Modelo estadístico que sigue la tendencia y repite el patrón de temporada de cada año.</dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Red neuronal LSTM</dt>
            <dd>Red neuronal que aprende patrones de los meses anteriores para estimar el siguiente.</dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">MAE (error absoluto medio)</dt>
            <dd>Cuántas personas, en promedio, se aleja el pronóstico de lo que realmente llegó cada mes.</dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">RMSE (raíz del error cuadrático medio)</dt>
            <dd>Parecido al MAE, pero castiga más los meses con errores muy grandes.</dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">MAPE (error porcentual medio)</dt>
            <dd>El error promedio como porcentaje de lo observado: permite comparar series de distinto tamaño.</dd>
          </div>
        </dl>
      </CardContent>

      <CardFooter className="flex-col items-start gap-1 border-t px-6 pt-4 pb-5 text-xs leading-relaxed text-muted-foreground">
        <PieFuente extra="Predicciones: laboratorios 1 y 2." />
      </CardFooter>
    </Card>
  )
}
