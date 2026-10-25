import { PronosticosView } from "@/features/pronosticos/components/pronosticos-view"
import { getMetricas, getPredicciones } from "@/features/pronosticos/pronosticos-api"
import { getMetadatos, getTotalMensual } from "@/features/shared/datos/datos-api"

export default async function PronosticosPage() {
  const [predicciones, metricas, metadatos, totalMensual] = await Promise.all([
    getPredicciones(),
    getMetricas(),
    getMetadatos(),
    getTotalMensual(),
  ])
  return <PronosticosView datos={{ predicciones, metricas, metadatos, totalMensual }} />
}
