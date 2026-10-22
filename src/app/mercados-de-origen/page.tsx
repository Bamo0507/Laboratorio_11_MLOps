import { MercadosDeOrigenView } from "@/features/mercados-de-origen/components/mercados-de-origen-view"
import { getContinentesAnual } from "@/features/mercados-de-origen/mercados-de-origen-api"

export default async function MercadosDeOrigenPage() {
  const datos = await getContinentesAnual()
  return <MercadosDeOrigenView datos={datos} />
}
