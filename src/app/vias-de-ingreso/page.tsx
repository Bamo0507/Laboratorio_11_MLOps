import { ViasDeIngresoView } from "@/features/vias-de-ingreso/components/vias-de-ingreso-view"
import { getFronterasAnual, getPaisesAereosAnual, getViasAnual } from "@/features/vias-de-ingreso/vias-de-ingreso-api"

export default async function ViasDeIngresoPage() {
  const [vias, fronteras, paises] = await Promise.all([getViasAnual(), getFronterasAnual(), getPaisesAereosAnual()])
  return <ViasDeIngresoView datos={{ vias, fronteras, paises }} />
}
