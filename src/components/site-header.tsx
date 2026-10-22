"use client"

import { usePathname } from "next/navigation"

import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { seccionActual } from "@/config/secciones"

export function SiteHeader() {
  const { titulo } = seccionActual(usePathname())

  return (
    <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <SidebarTrigger className="size-10 text-muted-foreground hover:text-foreground [&_svg:not([class*='size-'])]:size-5" />
      <Separator orientation="vertical" className="my-5" />
      <h1 className="font-heading text-lg font-semibold text-primary">
        {titulo}
      </h1>
    </header>
  )
}
