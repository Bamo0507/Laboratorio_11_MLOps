export function mesPublicado(fecha: string): string {
  const [anio, mes] = fecha.split("-").map(Number)
  return new Intl.DateTimeFormat("es-GT", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(anio, mes - 1, 1)))
}

export function mesCortoPublicado(fecha: string): string {
  const [anio, mes] = fecha.split("-").map(Number)
  return new Intl.DateTimeFormat("es-GT", { month: "short", year: "2-digit", timeZone: "UTC" }).format(new Date(Date.UTC(anio, mes - 1, 1)))
}

export function fechaPublicacion(fecha: string): string {
  return new Intl.DateTimeFormat("es-GT", { dateStyle: "long", timeStyle: "short", timeZone: "America/Guatemala" }).format(new Date(fecha))
}
