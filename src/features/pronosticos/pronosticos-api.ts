import "server-only"

import { carpetaPublicaciones, leerPublicacionAprobada } from "./publicaciones"
import type { EstadoPronosticos } from "./types"

export async function getPronosticosPublicados(): Promise<EstadoPronosticos> {
  try {
    const datos = await leerPublicacionAprobada(carpetaPublicaciones())
    return datos ? { estado: "disponible", datos } : { estado: "no_disponible", motivo: "sin_version_aprobada" }
  } catch (error) {
    console.error("No se pudo verificar la version aprobada de estimaciones.", error)
    return { estado: "no_disponible", motivo: "lectura_invalida" }
  }
}
