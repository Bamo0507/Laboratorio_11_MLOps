import { InicioView } from "@/features/inicio/components/inicio-view"
import { getMetadatos } from "@/features/shared/datos/datos-api"

export default async function InicioPage() {
  const metadatos = await getMetadatos()
  return <InicioView metadatos={metadatos} />
}
