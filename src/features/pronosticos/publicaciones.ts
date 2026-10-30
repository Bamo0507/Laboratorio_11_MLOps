import { createHash } from "node:crypto"
import { readFile, realpath } from "node:fs/promises"
import path from "node:path"

import type { PronosticoPublicado } from "./types"

const HUELLA = /^[a-f0-9]{64}$/
const IDENTIFICADOR = /^[a-f0-9]{32}$/
const MES = /^(\d{4})-(0[1-9]|1[0-2])$/
const FECHA_MENSUAL = /^\d{4}-(0[1-9]|1[0-2])-01$/
const FECHA_CON_ZONA = /T.*(?:Z|[+-]\d{2}:\d{2})$/

function exigir(condicion: unknown, mensaje: string): asserts condicion {
  if (!condicion) throw new Error(mensaje)
}

function objeto(valor: unknown): Record<string, unknown> {
  exigir(valor !== null && typeof valor === "object" && !Array.isArray(valor), "Se esperaba un objeto de publicacion")
  return valor as Record<string, unknown>
}

function texto(valor: unknown): string {
  exigir(typeof valor === "string" && valor.trim().length > 0, "Falta un texto requerido")
  return valor
}

function numero(valor: unknown): number {
  exigir(typeof valor === "number" && Number.isFinite(valor), "El valor debe ser numerico y finito")
  return valor
}

function indiceMes(valor: string): number {
  const coincidencia = MES.exec(valor)
  exigir(coincidencia, "El mes no tiene un formato valido")
  return Number(coincidencia[1]) * 12 + Number(coincidencia[2]) - 1
}

function mismoNumero(a: number, b: number): boolean {
  // Tolerancia de representacion, sin intervenir en la regla de desempeno.
  return Math.abs(a - b) <= 1e-8 + 1e-12 * Math.abs(b)
}

function dentroDe(raiz: string, archivo: string): boolean {
  const relativa = path.relative(raiz, archivo)
  return relativa !== ".." && !relativa.startsWith(`..${path.sep}`) && !path.isAbsolute(relativa)
}

/** Configuracion exclusiva del servidor. El valor predeterminado es relativo al repositorio. */
export function carpetaPublicaciones(): string {
  return path.resolve(process.cwd(), process.env.TURISMO_PUBLICACIONES_DIR?.trim() || "pipeline/data/processed/publicaciones")
}

/** Lee una sola instantanea aprobada. No busca candidatos ni recorre versiones alternativas. */
export async function leerPublicacionAprobada(directorio: string): Promise<PronosticoPublicado | null> {
  let raiz: string
  let rutaIndicador: string
  try {
    raiz = await realpath(directorio)
    rutaIndicador = await realpath(path.join(raiz, "vigente.json"))
  } catch (error) {
    if (error instanceof Error && "code" in error && error.code === "ENOENT") return null
    throw error
  }
  exigir(dentroDe(raiz, rutaIndicador), "El indicador esta fuera de publicaciones")
  const indicador = objeto(JSON.parse(await readFile(rutaIndicador, "utf8")))
  const version = texto(indicador.version)
  exigir(HUELLA.test(version), "La version no tiene un identificador valido")
  const relativa = `versiones/${version}.json`
  exigir(indicador.archivo === relativa, "El indicador no apunta al archivo esperado")
  const archivo = await realpath(path.join(raiz, relativa))
  exigir(dentroDe(raiz, archivo), "El archivo esta fuera de publicaciones")
  const contenido = await readFile(archivo)
  exigir(createHash("sha256").update(contenido).digest("hex") === indicador.sha256, "La version no conserva su integridad")
  const publicada = objeto(JSON.parse(contenido.toString("utf8")))
  exigir(publicada.version === version && publicada.version_esquema === 1, "La version o el esquema no coincide")
  exigir(publicada.publicacion_autorizada === true && publicada.supera_regla_desempeno === true, "La version no esta aprobada")
  exigir(objeto(publicada.comparabilidad).observaciones_comparables === true, "No hay observaciones comparables")
  const poblacion = objeto(publicada.poblacion)
  const destino = texto(poblacion.destino)
  exigir(poblacion.unidad === "llegadas_por_mes", "La unidad no es la esperada")
  const identificador = texto(publicada.id_ejecucion)
  exigir(IDENTIFICADOR.test(identificador), "Falta el identificador de ejecucion")
  const fechaGeneracion = texto(publicada.fecha_generacion)
  exigir(FECHA_CON_ZONA.test(fechaGeneracion) && Number.isFinite(Date.parse(fechaGeneracion)), "La fecha de generacion no es valida")
  exigir(indicador.fecha_generacion === fechaGeneracion, "La fecha del indicador no coincide")
  const periodo = objeto(publicada.periodo)
  const inicio = texto(periodo.inicio)
  const fin = texto(periodo.fin)
  const primerMes = indiceMes(inicio)
  const meses = indiceMes(fin) - primerMes + 1
  exigir(meses > 0 && periodo.meses === meses, "El periodo no es coherente")
  exigir(Array.isArray(publicada.estimaciones) && publicada.estimaciones.length === meses, "Faltan meses de estimaciones")
  const metricas = objeto(publicada.metricas)
  const sarima = objeto(metricas.sarima)
  const referencia = objeto(metricas.referencia)
  const mae = numero(sarima.mae)
  const rmse = numero(sarima.rmse)
  exigir(mae >= 0 && rmse >= 0 && mae < numero(referencia.mae) && rmse < numero(referencia.rmse), "La version no supera la regla de desempeno")
  let sumaAbsoluta = 0
  let sumaCuadrados = 0
  const estimaciones = publicada.estimaciones.map((valor, i) => {
    const fila = objeto(valor)
    const fecha = texto(fila.fecha)
    exigir(FECHA_MENSUAL.test(fecha) && indiceMes(fecha.slice(0, 7)) === primerMes + i, "Los meses no son consecutivos y unicos")
    exigir(fila.destino === destino && fila.unidad === poblacion.unidad, "Destino o unidad inconsistentes")
    exigir(fila.id_ejecucion === identificador && fila.fecha_generacion === fechaGeneracion && fila.version_procedimiento === version, "Los metadatos del mes no coinciden")
    const observado = numero(fila.observado)
    const estimado = numero(fila.valor)
    exigir(observado >= 0 && estimado > 0 && estimado === numero(fila.sarima), "Las cantidades del mes no son validas")
    const error = estimado - observado
    sumaAbsoluta += Math.abs(error)
    sumaCuadrados += error ** 2
    return { fecha: fecha.slice(0, 7), observado, valor: estimado }
  })
  exigir(mismoNumero(mae, sumaAbsoluta / meses) && mismoNumero(rmse, Math.sqrt(sumaCuadrados / meses)), "Las metricas no corresponden a las estimaciones")
  // No se envian al cliente identificadores, rutas, configuracion ni parametros del modelo.
  return { destino, fechaGeneracion, periodo: { inicio, fin, meses }, metricas: { mae, rmse }, estimaciones, demostracion: publicada.datos_sinteticos === true }
}
