import { TemporadasView } from "@/features/temporadas/components/temporadas-view"
import { getContinentesMensual } from "@/features/temporadas/temporadas-api"

export default async function TemporadasPage() {
  const datos = await getContinentesMensual()
  return <TemporadasView datos={datos} />
}
