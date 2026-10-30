import { connection } from "next/server"

import { PronosticosView } from "@/features/pronosticos/components/pronosticos-view"
import { getPronosticosPublicados } from "@/features/pronosticos/pronosticos-api"

export default async function PronosticosPage() {
  // La version puede cambiar despues de construir la aplicacion. Se consulta por solicitud.
  await connection()
  const estado = await getPronosticosPublicados()
  return <PronosticosView estado={estado} />
}
