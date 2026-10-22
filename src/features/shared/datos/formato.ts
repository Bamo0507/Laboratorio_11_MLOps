const LOCALE = "es-GT"

const entero = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 })
const compacto = new Intl.NumberFormat(LOCALE, { notation: "compact", maximumFractionDigits: 1 })
const decimal = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1, minimumFractionDigits: 1 })

/** 2143694 -> "2,143,694" */
export const formatoPersonas = (valor: number) => entero.format(valor)

/** 2143694 -> "2.1 M" */
export const formatoCompacto = (valor: number) => compacto.format(valor)

/** 63.95 -> "64.0 %" */
export const formatoPorcentaje = (valor: number) => `${decimal.format(valor)} %`

/** Índice 2019 = 100 sin decimales: 139.3 -> "139" */
export const formatoIndice = (valor: number) => entero.format(valor)

/** Diferencia en puntos porcentuales: 1.2 -> "+1.2 pts" */
export const formatoPuntos = (valor: number) =>
  `${valor >= 0 ? "+" : "−"}${decimal.format(Math.abs(valor))} pts`

/** 12.34 -> "+12.3 %" ; -4 -> "−4.0 %" */
export const formatoVariacion = (valor: number) =>
  `${valor >= 0 ? "+" : "−"}${decimal.format(Math.abs(valor))} %`
