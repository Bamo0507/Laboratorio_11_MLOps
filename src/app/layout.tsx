import type { Metadata } from "next"
import { Instrument_Sans, Inter } from "next/font/google"
import { cookies } from "next/headers"

import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import "./globals.css"

// Instrument Sans: títulos, etiquetas y textos. Inter: cifras de KPIs, ejes y tablas.
const instrumentSans = Instrument_Sans({
  variable: "--font-instrument-sans",
  subsets: ["latin"],
})

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "Turismo internacional en Guatemala",
  description:
    "Tablero interactivo sobre la llegada de viajeros internacionales a Guatemala, 2009 a junio de 2026.",
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  // La barra lateral arranca colapsada; si el usuario la expande, se recuerda al recargar.
  const cookieStore = await cookies()
  const sidebarAbierta = cookieStore.get("sidebar_state")?.value === "true"

  return (
    <html
      lang="es"
      className={`${instrumentSans.variable} ${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <TooltipProvider>
          <SidebarProvider defaultOpen={sidebarAbierta}>
            <AppSidebar />
            <SidebarInset>
              <SiteHeader />
              <main className="flex flex-1 flex-col p-6">{children}</main>
            </SidebarInset>
          </SidebarProvider>
        </TooltipProvider>
      </body>
    </html>
  )
}
