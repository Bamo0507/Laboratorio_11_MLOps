import type { ModeloId, SerieId } from "@/features/shared/datos/types"

/**
 * Predicción mensual de un modelo sobre el periodo de prueba (abr. 2021 a jun. 2026).
 * La LSTM no tiene banda de incertidumbre: sus límites vienen en null.
 */
export type Prediccion = {
  serie: SerieId
  modelo: ModeloId
  fecha: string
  real: number
  prediccion: number
  limiteInferior: number | null
  limiteSuperior: number | null
}

/** Error de cada modelo en el periodo de prueba (MAPE en %). */
export type Metrica = {
  serie: SerieId
  modelo: ModeloId
  mae: number
  rmse: number
  mape: number
}

/** Datos minimos de una version aprobada para su consulta directiva. */
export type EstimacionPublicada = {
  fecha: string
  observado: number
  valor: number
}

export type PronosticoPublicado = {
  destino: string
  fechaGeneracion: string
  periodo: { inicio: string; fin: string; meses: number }
  metricas: { mae: number; rmse: number }
  estimaciones: EstimacionPublicada[]
  demostracion: boolean
}

export type EstadoPronosticos =
  | { estado: "disponible"; datos: PronosticoPublicado }
  | { estado: "no_disponible"; motivo: "sin_version_aprobada" | "lectura_invalida" }
