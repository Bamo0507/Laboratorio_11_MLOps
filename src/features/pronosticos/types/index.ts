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
