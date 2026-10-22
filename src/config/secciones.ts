import {
  CalendarRange,
  Earth,
  House,
  Route,
  TrendingUp,
  type LucideIcon,
} from "lucide-react"

export type Seccion = {
  titulo: string
  href: string
  icono: LucideIcon
}

// Orden de la barra lateral, igual que en el bosquejo del documento de diseño.
export const SECCIONES: Seccion[] = [
  { titulo: "Inicio", href: "/", icono: House },
  { titulo: "Mercados de origen", href: "/mercados-de-origen", icono: Earth },
  { titulo: "Vías de ingreso", href: "/vias-de-ingreso", icono: Route },
  { titulo: "Temporadas", href: "/temporadas", icono: CalendarRange },
  { titulo: "Pronósticos", href: "/pronosticos", icono: TrendingUp },
]

export function seccionActual(pathname: string): Seccion {
  return (
    SECCIONES.find((s) => s.href !== "/" && pathname.startsWith(s.href)) ??
    SECCIONES[0]
  )
}
