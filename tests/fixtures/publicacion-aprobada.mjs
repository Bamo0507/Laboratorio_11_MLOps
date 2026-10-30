import { createHash } from "node:crypto"
import { mkdir, writeFile } from "node:fs/promises"
import path from "node:path"

// Solo datos sinteticos para probar el lector y la presentacion. Nunca se activan en produccion.
export function publicacionSintetica(nombre = "primera") {
  const version = createHash("sha256").update(nombre).digest("hex")
  const id = "1234567890abcdef1234567890abcdef"
  const fecha = "2026-10-29T18:00:00+00:00"
  const observados = [100000, 90000, 120000, 110000, 100000, 130000]
  const errores = [1000, -2000, 1500, -500, 2000, -1000]
  const mae = errores.reduce((a, e) => a + Math.abs(e), 0) / errores.length
  const rmse = Math.sqrt(errores.reduce((a, e) => a + e ** 2, 0) / errores.length)
  return {
    version_esquema: 1, version, publicacion_autorizada: true, supera_regla_desempeno: true,
    datos_sinteticos: true, id_ejecucion: id, id_ejecucion_mlflow: id, fecha_generacion: fecha,
    poblacion: { destino: "Guatemala", unidad: "llegadas_por_mes" },
    periodo: { inicio: "2026-01", fin: "2026-06", meses: 6 },
    comparabilidad: { observaciones_comparables: true },
    metricas: { sarima: { mae, rmse }, referencia: { mae: 5000, rmse: 5000 } },
    estimaciones: observados.map((observado, i) => ({
      fecha: `2026-0${i + 1}-01`, observado, sarima: observado + errores[i], valor: observado + errores[i],
      destino: "Guatemala", unidad: "llegadas_por_mes", id_ejecucion: id, id_ejecucion_mlflow: id,
      fecha_generacion: fecha, version_procedimiento: version,
    })),
  }
}

export async function escribirPublicacion(directorio, publicacion, activar = true) {
  await mkdir(path.join(directorio, "versiones"), { recursive: true })
  const archivo = `versiones/${publicacion.version}.json`
  const contenido = JSON.stringify(publicacion)
  await writeFile(path.join(directorio, archivo), contenido)
  if (activar) {
    await writeFile(path.join(directorio, "vigente.json"), JSON.stringify({
      version: publicacion.version, archivo,
      sha256: createHash("sha256").update(contenido).digest("hex"), fecha_generacion: publicacion.fecha_generacion,
    }))
  }
}
