import Link from "next/link"
import {
  ChevronRight,
  Filter,
  MousePointerClick,
  MousePointer2,
  PanelLeft,
  type LucideIcon,
} from "lucide-react"

import { Card } from "@/components/ui/card"
import { SECCIONES } from "@/features/shared/navegacion/secciones"
import type { Metadatos } from "@/features/shared/datos/types"

// Preguntas de gestión que responde cada sección (documento de diseño, «Alcance del Tablero»).
const PREGUNTAS: Record<string, string[]> = {
  "/mercados-de-origen": [
    "¿De qué continente se recibe la mayor cantidad de turismo?",
    "Tras la pandemia, ¿qué continente ha mostrado la mejor recuperación?",
  ],
  "/vias-de-ingreso": [
    "¿Cómo ha sido el crecimiento relativo de cada vía de ingreso al país?",
    "¿Cambiaron los países de los que más llegan visitantes por aire, antes y después de la pandemia?",
  ],
  "/temporadas": ["¿En qué meses del año llegan más visitantes y cambia según el continente?"],
  "/pronosticos": ["¿Qué estimaciones de llegadas están aprobadas y cuánto se equivocan al compararlas con los datos?"],
}

const INTERACCIONES: { icono: LucideIcon; titulo: string; texto: string }[] = [
  {
    icono: Filter,
    titulo: "Filtros por sección",
    texto: "Cada sección tiene sus propios selectores (año, periodo, continente o modelo) y solo afectan a sus gráficos.",
  },
  {
    icono: MousePointerClick,
    titulo: "Gráficos enlazados",
    texto: "Al hacer clic en una barra o elegir una opción, el gráfico de abajo muestra el detalle de esa selección.",
  },
  {
    icono: MousePointer2,
    titulo: "Valores exactos",
    texto: "Pasa el cursor sobre cualquier gráfico para ver la cifra exacta de cada punto o barra.",
  },
  {
    icono: PanelLeft,
    titulo: "Navegación",
    texto: "Usa la barra lateral para moverte entre secciones; el botón de la parte superior la expande o la contrae.",
  },
]

function mesAnio(fecha: string) {
  const [anio, mes] = fecha.split("-").map(Number)
  const nombre = new Intl.DateTimeFormat("es-GT", { month: "long" }).format(new Date(anio, mes - 1, 1))
  return `${nombre} de ${anio}`
}

function Muestra({ color, forma = "punto" }: { color: string; forma?: "punto" | "linea" | "punteada" | "franja" }) {
  if (forma === "punto") return <span aria-hidden className="size-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
  if (forma === "franja") return <span aria-hidden className="h-3 w-6 shrink-0 rounded-sm" style={{ backgroundColor: color, opacity: 0.3 }} />
  return (
    <span
      aria-hidden
      className={`w-6 shrink-0 border-t-2 ${forma === "punteada" ? "border-dashed" : ""}`}
      style={{ borderColor: color }}
    />
  )
}

function Fila({ muestra, children }: { muestra: React.ReactNode; children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-3 text-sm leading-snug text-foreground">
      <span className="flex w-6 shrink-0 justify-center">{muestra}</span>
      <span>{children}</span>
    </li>
  )
}

export function InicioView({ metadatos }: { metadatos: Metadatos }) {
  const secciones = SECCIONES.filter((s) => s.href !== "/")

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-10">
      <section className="flex flex-col gap-4 pt-2">
        <h2 className="max-w-[24ch] font-heading text-3xl leading-tight font-semibold text-balance text-primary md:text-4xl">
          Turismo internacional en Guatemala
        </h2>
        <p className="max-w-[70ch] text-base leading-relaxed text-muted-foreground">
          Este tablero muestra cuántos viajeros internacionales (turistas y excursionistas) llegan a Guatemala, de dónde
          vienen, por dónde entran, en qué meses y qué tan bien se pueden pronosticar sus llegadas. Cubre de{" "}
          {mesAnio(metadatos.periodo.inicio)} a {mesAnio(metadatos.periodo.fin)} y está pensado para apoyar decisiones
          de promoción y planificación, sin necesidad de conocimientos de estadística.
        </p>
        <dl className="flex flex-wrap gap-x-8 gap-y-3 text-sm">
          {[
            ["Fuente", "Base de Migración"],
            ["Periodo", `${metadatos.periodo.inicio.slice(0, 4)} a ${metadatos.periodo.fin.slice(0, 4)}`],
            ["Detalle", "Mensual, por continente, vía, frontera y país (agrupados desde 2023)"],
          ].map(([termino, valor]) => (
            <div key={termino} className="flex flex-col gap-0.5">
              <dt className="text-muted-foreground">{termino}</dt>
              <dd className="font-medium text-foreground">{valor}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="titulo-secciones" className="flex flex-col gap-4">
        <h3 id="titulo-secciones" className="font-heading text-lg font-semibold text-foreground">
          ¿Qué vas a encontrar?
        </h3>
        <Card className="gap-0 py-0">
          <ul className="divide-y">
            {secciones.map(({ titulo, href, icono: Icono }) => (
              <li key={href}>
                <Link
                  href={href}
                  className="group flex items-center gap-4 px-5 py-5 transition-colors duration-150 hover:bg-accent/45 focus-visible:bg-accent/45 focus-visible:outline-none"
                >
                  <span className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-accent text-primary transition-colors duration-150 group-hover:bg-primary group-hover:text-primary-foreground group-focus-visible:bg-primary group-focus-visible:text-primary-foreground">
                    <Icono className="size-5" aria-hidden />
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col gap-1">
                    <span className="font-heading text-base font-semibold text-foreground transition-colors duration-150 group-hover:text-primary">{titulo}</span>
                    {PREGUNTAS[href]?.map((pregunta) => (
                      <span key={pregunta} className="text-sm leading-snug text-muted-foreground">
                        {pregunta}
                      </span>
                    ))}
                  </span>
                  <ChevronRight
                    className="size-5 shrink-0 text-muted-foreground transition-[transform,color] duration-150 group-hover:translate-x-0.5 group-hover:text-primary"
                    aria-hidden
                  />
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <section aria-labelledby="titulo-interactuar" className="flex flex-col gap-4">
        <h3 id="titulo-interactuar" className="font-heading text-lg font-semibold text-foreground">
          ¿Cómo interactuar?
        </h3>
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {INTERACCIONES.map(({ icono: Icono, titulo, texto }) => (
            <li key={titulo} className="flex">
              <Card className="flex-1 gap-3 px-5 py-5">
                <span className="flex size-11 items-center justify-center rounded-lg bg-accent text-primary">
                  <Icono className="size-5" aria-hidden />
                </span>
                <span className="font-heading text-base font-semibold text-foreground">{titulo}</span>
                <span className="text-sm leading-relaxed text-muted-foreground">{texto}</span>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="titulo-leer" className="flex flex-col gap-4">
        <h3 id="titulo-leer" className="font-heading text-lg font-semibold text-foreground">
          ¿Cómo leer los gráficos?
        </h3>
        <Card className="grid gap-0 py-0 md:grid-cols-2 lg:grid-cols-3 lg:divide-x">
          <div className="flex flex-col gap-4 px-6 py-6">
            <p className="font-heading text-base font-semibold text-foreground">Cada color significa siempre lo mismo</p>
            <div className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">Continentes</p>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-2">
                {metadatos.continentes.map((c) => (
                  <Fila key={c.id} muestra={<Muestra color={`var(--continente-${c.id})`} />}>
                    {c.nombre}
                  </Fila>
                ))}
              </ul>
            </div>
            <div className="flex flex-col gap-2">
              <p className="text-sm text-muted-foreground">Vías de ingreso</p>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-2">
                {metadatos.vias.map((v) => (
                  <Fila key={v.id} muestra={<Muestra color={`var(--via-${v.id})`} />}>
                    {v.nombre}
                  </Fila>
                ))}
              </ul>
            </div>
          </div>

          <div className="flex flex-col gap-4 border-t px-6 py-6 md:border-t-0 md:border-l lg:border-l-0">
            <p className="font-heading text-base font-semibold text-foreground">Lo observado y lo estimado</p>
            <ul className="flex flex-col gap-3">
              <Fila muestra={<Muestra color="var(--observado)" forma="linea" />}>
                Línea continua: lo que realmente ocurrió.
              </Fila>
              <Fila muestra={<Muestra color="var(--estimacion)" forma="punteada" />}>
                Línea punteada: estimación de un modelo, no un dato medido.
              </Fila>
              <Fila muestra={<Muestra color="var(--estimacion)" forma="franja" />}>
                Franja: rango en el que suele quedar el valor real.
              </Fila>
              <Fila muestra={<Muestra color="var(--contexto)" forma="linea" />}>
                Gris: contexto para comparar con lo resaltado.
              </Fila>
            </ul>
          </div>

          <div className="flex flex-col gap-4 border-t px-6 py-6 md:col-span-2 lg:col-span-1 lg:border-t-0">
            <p className="font-heading text-base font-semibold text-foreground">Datos a tener en cuenta</p>
            <ul className="flex flex-col gap-3 text-sm leading-relaxed text-muted-foreground">
              <li>
                <span className="font-medium text-foreground">Sin dato</span> significa que en ese periodo no hubo
                registro (por ejemplo, el cierre de fronteras en 2020); no equivale a cero.
              </li>
              <li>
                <span className="font-medium text-foreground">{metadatos.anioParcial}</span> es un año parcial: solo
                tiene datos de enero a junio, así que no se compara directamente con años completos.
              </li>
              <li>
                <span className="font-medium text-foreground">Sin residentes en Guatemala.</span> La base dejó de
                registrarlos en 2023, así que las secciones descriptivas los excluyen en todo el periodo para comparar el
                mismo grupo de visitantes. Los pronósticos sí los incluyen hasta 2022, como en los laboratorios.
              </li>
              <li>
                <span className="font-medium text-foreground">Los pronósticos</span> son estimaciones de modelos: en
                su sección se muestra qué tanto se equivoca cada uno frente a lo que realmente ocurrió.
              </li>
            </ul>
          </div>
        </Card>
      </section>

      <p className="text-sm text-muted-foreground">
        Fuente: {metadatos.fuente}. Las cifras muestran relaciones observadas en los datos; no indican por sí solas sus
        causas.
      </p>
    </div>
  )
}
