import { Card } from "@/components/ui/card"

/** Tarjeta de indicador clave: etiqueta, valor y detalle con su comparación. */
export function Kpi({ etiqueta, valor, detalle }: { etiqueta: string; valor: React.ReactNode; detalle?: React.ReactNode }) {
  return (
    <Card className="gap-2 px-5 py-5">
      <p className="text-sm text-muted-foreground">{etiqueta}</p>
      <p className="font-heading text-2xl leading-tight font-semibold text-foreground first-letter:uppercase">{valor}</p>
      {detalle && <div className="flex flex-col gap-0.5 text-sm leading-snug text-muted-foreground">{detalle}</div>}
    </Card>
  )
}

export function FilaKpis({ children }: { children: React.ReactNode }) {
  return (
    <section aria-label="Indicadores clave" className="grid gap-4 md:grid-cols-3">
      {children}
    </section>
  )
}

/** Cifra destacada dentro de un texto: Inter con números tabulares. */
export function Cifra({ children }: { children: React.ReactNode }) {
  return <span className="font-data font-medium text-foreground">{children}</span>
}

/** Punto de color que identifica una entidad (continente, vía) junto a su nombre. */
export function Muestra({ color }: { color: string }) {
  return <span aria-hidden className="mr-2 inline-block size-3 rounded-full align-middle" style={{ backgroundColor: color }} />
}
