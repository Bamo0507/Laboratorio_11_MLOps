import assert from "node:assert/strict"
import { mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises"
import os from "node:os"
import path from "node:path"
import { afterEach, beforeEach, test } from "node:test"

import { carpetaPublicaciones, leerPublicacionAprobada } from "../src/features/pronosticos/publicaciones.ts"
import { escribirPublicacion, publicacionSintetica } from "./fixtures/publicacion-aprobada.mjs"

let raiz
beforeEach(async () => { raiz = await mkdtemp(path.join(os.tmpdir(), "lab11-publicaciones-")) })
afterEach(async () => { await rm(raiz, { recursive: true, force: true }) })

test("sin indicador aprobado devuelve no disponible aunque exista un candidato", async () => {
  assert.equal(await leerPublicacionAprobada(path.join(raiz, "ausente")), null)
  await writeFile(path.join(raiz, "06_candidato.json"), JSON.stringify(publicacionSintetica()))
  assert.equal(await leerPublicacionAprobada(raiz), null)
})

test("lee el contrato aprobado y limita los datos que llegan al navegador", async () => {
  const publicada = publicacionSintetica()
  await escribirPublicacion(raiz, publicada)
  const visible = await leerPublicacionAprobada(raiz)
  assert.equal(visible.destino, "Guatemala")
  assert.equal(visible.estimaciones.length, 6)
  assert.equal(visible.fechaGeneracion, publicada.fecha_generacion)
  assert.deepEqual(visible.metricas, publicada.metricas.sarima)
  assert.equal(visible.demostracion, true)
  assert.equal("id_ejecucion" in visible, false)
  assert.equal("version" in visible, false)
  assert.equal("comparabilidad" in visible, false)
  assert.deepEqual(Object.keys(visible.estimaciones[0]), ["fecha", "observado", "valor"])
})

test("un candidato nuevo o una actualizacion rechazada no reemplazan la version aprobada", async () => {
  await escribirPublicacion(raiz, publicacionSintetica())
  const anterior = await leerPublicacionAprobada(raiz)
  await escribirPublicacion(raiz, { ...publicacionSintetica("rechazada"), publicacion_autorizada: false }, false)
  await writeFile(path.join(raiz, "07_publicacion.json"), JSON.stringify({ estado: "no_publicado" }))
  assert.deepEqual(await leerPublicacionAprobada(raiz), anterior)
})

test("consulta la nueva version aprobada sin cache y conserva el archivo anterior", async () => {
  const primera = publicacionSintetica()
  await escribirPublicacion(raiz, primera)
  const segunda = publicacionSintetica("segunda")
  segunda.fecha_generacion = "2026-10-29T19:00:00+00:00"
  segunda.estimaciones.forEach((f) => { f.fecha_generacion = segunda.fecha_generacion })
  await escribirPublicacion(raiz, segunda)
  assert.equal((await leerPublicacionAprobada(raiz)).fechaGeneracion, segunda.fecha_generacion)
  assert.equal(JSON.parse(await readFile(path.join(raiz, `versiones/${primera.version}.json`), "utf8")).version, primera.version)
})

test("rechaza un archivo alterado aunque conserve el nombre de la version", async () => {
  const publicada = publicacionSintetica()
  await escribirPublicacion(raiz, publicada)
  await writeFile(path.join(raiz, `versiones/${publicada.version}.json`), "{}")
  await assert.rejects(leerPublicacionAprobada(raiz), /integridad/)
})

test("no interpreta una autorizacion falsa como una version aprobada", async () => {
  await escribirPublicacion(raiz, { ...publicacionSintetica(), publicacion_autorizada: false })
  await assert.rejects(leerPublicacionAprobada(raiz), /no esta aprobada/)
})

test("rechaza metadatos incompletos o inconsistentes en los registros mensuales", async () => {
  for (const campo of ["destino", "unidad", "id_ejecucion", "fecha_generacion", "version_procedimiento"]) {
    const publicada = publicacionSintetica()
    delete publicada.estimaciones[0][campo]
    await escribirPublicacion(raiz, publicada)
    await assert.rejects(leerPublicacionAprobada(raiz), /no coinciden|inconsistentes/)
  }
})

test("no acepta meses incompletos, repetidos o fuera del periodo", async () => {
  for (const cambio of ["ausente", "repetido", "fuera"]) {
    const publicada = publicacionSintetica()
    if (cambio === "ausente") publicada.estimaciones.pop()
    else publicada.estimaciones[1].fecha = cambio === "repetido" ? publicada.estimaciones[0].fecha : "2027-01-01"
    await escribirPublicacion(raiz, publicada)
    await assert.rejects(leerPublicacionAprobada(raiz), /meses/)
  }
})

test("rechaza valores negativos, ausentes o distintos del pronostico certificado", async () => {
  for (const valor of [-1, null, 123]) {
    const publicada = publicacionSintetica()
    publicada.estimaciones[0].valor = valor
    await escribirPublicacion(raiz, publicada)
    await assert.rejects(leerPublicacionAprobada(raiz), /validas|numerico/)
  }
})

test("comprueba que MAE y RMSE correspondan a los meses mostrados", async () => {
  const publicada = publicacionSintetica()
  publicada.metricas.sarima.mae += 10
  await escribirPublicacion(raiz, publicada)
  await assert.rejects(leerPublicacionAprobada(raiz), /metricas no corresponden/)
})

test("rechaza una version que no supera a la referencia o no tiene observaciones comparables", async () => {
  for (const cambio of ["desempeno", "comparabilidad"]) {
    const publicada = publicacionSintetica()
    if (cambio === "desempeno") publicada.metricas.referencia = { ...publicada.metricas.sarima }
    else publicada.comparabilidad.observaciones_comparables = false
    await escribirPublicacion(raiz, publicada)
    await assert.rejects(leerPublicacionAprobada(raiz), /regla de desempeno|comparables/)
  }
})

test("impide que el indicador lea otra ruta o una version faltante", async () => {
  const publicada = publicacionSintetica()
  await escribirPublicacion(raiz, publicada)
  const ruta = path.join(raiz, "vigente.json")
  const indicador = JSON.parse(await readFile(ruta, "utf8"))
  await writeFile(ruta, JSON.stringify({ ...indicador, archivo: "../06_candidato.json" }))
  await assert.rejects(leerPublicacionAprobada(raiz), /archivo esperado/)
  await writeFile(ruta, JSON.stringify({ ...indicador, version: "a".repeat(64), archivo: `versiones/${"a".repeat(64)}.json` }))
  await assert.rejects(leerPublicacionAprobada(raiz), /ENOENT/)
})

test("no sigue enlaces simbolicos hacia archivos fuera de publicaciones", async (t) => {
  if (process.platform === "win32") return t.skip("La creacion de symlinks puede requerir permisos adicionales")
  const directorio = path.join(raiz, "publicaciones")
  const publicada = publicacionSintetica()
  await escribirPublicacion(directorio, publicada)
  const ruta = path.join(directorio, `versiones/${publicada.version}.json`)
  const copia = await readFile(ruta)
  const fuera = path.join(raiz, "fuera.json")
  await writeFile(fuera, copia)
  await rm(ruta)
  await symlink(fuera, ruta)
  await assert.rejects(leerPublicacionAprobada(directorio), /fuera de publicaciones/)
})

test("las rutas predeterminadas y configuradas se resuelven sin rutas personales", () => {
  const anterior = process.env.TURISMO_PUBLICACIONES_DIR
  try {
    delete process.env.TURISMO_PUBLICACIONES_DIR
    assert.equal(carpetaPublicaciones(), path.resolve("pipeline/data/processed/publicaciones"))
    process.env.TURISMO_PUBLICACIONES_DIR = "pipeline/data/processed/otra-carpeta"
    assert.equal(carpetaPublicaciones(), path.resolve("pipeline/data/processed/otra-carpeta"))
  } finally {
    if (anterior === undefined) delete process.env.TURISMO_PUBLICACIONES_DIR
    else process.env.TURISMO_PUBLICACIONES_DIR = anterior
  }
})

test("una fecha de generacion invalida o un run ausente impiden la consulta", async () => {
  for (const cambio of ["fecha", "run"]) {
    const publicada = publicacionSintetica()
    if (cambio === "fecha") publicada.fecha_generacion = "sin fecha"
    else delete publicada.id_ejecucion
    await escribirPublicacion(raiz, publicada)
    await assert.rejects(leerPublicacionAprobada(raiz), /fecha de generacion|texto requerido/)
  }
})
