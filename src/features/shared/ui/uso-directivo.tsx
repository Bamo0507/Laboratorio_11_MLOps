/** Línea fija bajo la descripción de cada gráfico: para qué decisión le sirve a un directivo. */
export function UsoDirectivo({ children }: { children: React.ReactNode }) {
  return (
    <p className="max-w-[80ch] text-sm leading-relaxed text-muted-foreground">
      <span className="font-medium text-foreground">Para qué sirve:</span> {children}
    </p>
  )
}
