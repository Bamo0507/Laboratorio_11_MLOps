"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Plane } from "lucide-react"

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { SECCIONES, seccionActual } from "@/config/secciones"

export function AppSidebar() {
  const pathname = usePathname()
  const activa = seccionActual(pathname)

  return (
    <Sidebar collapsible="icon">
      {/* Identidad del tablero: no es interactiva, por eso no lleva hover */}
      <SidebarHeader className="h-16 justify-center border-b border-sidebar-border py-0">
        <div className="flex items-center gap-3 overflow-hidden px-1">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
            <Plane className="size-5" aria-hidden />
          </span>
          <span className="grid min-w-0 gap-0.5 leading-tight whitespace-nowrap">
            <span className="truncate font-heading text-[17px] font-semibold text-sidebar-accent-foreground">
              Turismo
            </span>
            <span className="truncate font-data text-[13px] text-sidebar-muted-foreground">
              Guatemala · 2009-2026
            </span>
          </span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup className="px-2.5 pt-4">
          <SidebarGroupContent>
            <SidebarMenu className="gap-2">
              {SECCIONES.map((seccion) => {
                const Icono = seccion.icono
                const esActiva = seccion.href === activa.href
                return (
                  <SidebarMenuItem key={seccion.href}>
                    <SidebarMenuButton
                      isActive={esActiva}
                      tooltip={seccion.titulo}
                      render={
                        <Link
                          href={seccion.href}
                          aria-current={esActiva ? "page" : undefined}
                        />
                      }
                      className="data-active:bg-sidebar-primary data-active:font-semibold data-active:text-sidebar-primary-foreground data-active:hover:bg-sidebar-primary data-active:hover:text-sidebar-primary-foreground"
                    >
                      <Icono aria-hidden />
                      <span>{seccion.titulo}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarRail />
    </Sidebar>
  )
}
