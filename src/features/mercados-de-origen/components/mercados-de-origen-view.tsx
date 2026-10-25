"use client"

import type { ContinenteAnual } from "../types"
import { useMercadosDeOrigen } from "../hooks/use-mercados-de-origen"
import { ContinentesBarrasChart } from "./continentes-barras-chart"
import { KpisMercados } from "./kpis-mercados"
import { RecuperacionChart } from "./recuperacion-chart"

export function MercadosDeOrigenView({ datos }: { datos: ContinenteAnual[] }) {
  const m = useMercadosDeOrigen(datos)

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <p className="max-w-[70ch] text-base leading-relaxed text-muted-foreground">
        De qué continentes llegan los visitantes internacionales a Guatemala y qué tanto se ha recuperado cada uno
        después de la pandemia. Elige un año para comparar los mercados y haz clic en un continente para seguir su
        recuperación.
      </p>

      <KpisMercados
        anio={m.anioSeleccionado}
        total={m.kpis.total}
        variacion={m.kpis.variacion}
        esParcial={m.kpis.esParcial}
        principal={m.kpis.principal}
        cambioPeso={m.kpis.cambioPeso}
        empatados={m.empatados}
        anioRecuperacion={m.ultimoAnioCompleto}
      />

      <ContinentesBarrasChart
        barras={m.barras}
        anios={m.anios}
        anioParcial={m.anioParcial}
        anioSeleccionado={m.anioSeleccionado}
        onCambiarAnio={m.setAnioSeleccionado}
        continenteResaltado={m.continenteResaltado}
        onSeleccionarContinente={m.setContinenteResaltado}
      />

      <RecuperacionChart
        serie={m.serieRecuperacion}
        recuperacionFinal={m.recuperacionFinal}
        mercadoPrincipal={m.mercadoPrincipal}
        empatados={m.empatados}
        ultimoAnio={m.ultimoAnioCompleto}
        continenteResaltado={m.continenteResaltado}
        onSeleccionarContinente={m.setContinenteResaltado}
      />
    </div>
  )
}
