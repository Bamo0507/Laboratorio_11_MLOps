// Catálogos compartidos por todas las features. Los ids coinciden con los
// tokens de color de globals.css (--continente-<id>, --via-<id>).

export type ContinenteId = "norte" | "centro" | "sur" | "europa" | "asia" | "resto"
export type ViaId = "aerea" | "terrestre" | "maritima"
export type SerieId = "total" | "aurora"
export type ModeloId = "ses" | "sarima" | "lstm"

type Catalogo<T extends string> = { id: T; nombre: string }

export type Metadatos = {
  fuente: string
  periodo: { inicio: string; fin: string }
  anioParcial: number
  anioBaseRecuperacion: number
  finEntrenamiento: string
  generado: string
  continentes: Catalogo<ContinenteId>[]
  vias: Catalogo<ViaId>[]
  series: Catalogo<SerieId>[]
  modelos: Catalogo<ModeloId>[]
}

/** Total mensual de llegadas al país (fecha en formato YYYY-MM). */
export type LlegadaMensual = { fecha: string; viajeros: number }
