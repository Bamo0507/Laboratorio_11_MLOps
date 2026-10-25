"use client"

import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import type { ModeloId, SerieId } from "@/features/shared/datos/types"

import { usePronosticos, type Datos } from "../hooks/use-pronosticos"
import { ErrorChart } from "./error-chart"
import { KpisPronosticos } from "./kpis-pronosticos"
import { PrediccionChart } from "./prediccion-chart"
import { TablaMetricas } from "./tabla-metricas"

const CLASE_OPCION =
  "h-10 cursor-pointer px-3 text-sm transition-colors duration-150 hover:border-foreground/30 hover:bg-muted hover:text-foreground data-pressed:border-primary data-pressed:bg-accent data-pressed:font-medium data-pressed:text-accent-foreground data-pressed:hover:bg-accent"

export function PronosticosView({ datos }: { datos: Datos }) {
  const p = usePronosticos(datos)

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <p className="max-w-[70ch] text-base leading-relaxed text-muted-foreground">
        Qué tan bien anticiparon las llegadas los tres modelos de pronóstico de los laboratorios anteriores. Elige una
        serie y un modelo para comparar lo estimado contra lo que realmente llegó, y acota el periodo para ver el error
        mes a mes.
      </p>

      <KpisPronosticos
        nombreSerie={p.nombreSerie[p.serie]}
        nombreModelo={p.nombreModelo}
        mejor={p.mejor}
        peor={p.peor}
        seleccionado={p.seleccionado}
      />

      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-foreground">Serie</span>
          <ToggleGroup
            aria-label="Serie"
            value={[p.serie]}
            onValueChange={(v) => v[0] && p.setSerie(v[0] as SerieId)}
            variant="outline"
            spacing={2}
            className="flex-wrap"
          >
            {datos.metadatos.series.map((s) => (
              <ToggleGroupItem key={s.id} value={s.id} className={CLASE_OPCION}>
                {s.nombre}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-foreground">Modelo</span>
          <ToggleGroup
            aria-label="Modelo"
            value={[p.modelo]}
            onValueChange={(v) => v[0] && p.setModelo(v[0] as ModeloId)}
            variant="outline"
            spacing={2}
            className="flex-wrap"
          >
            {datos.metadatos.modelos.map((m) => (
              <ToggleGroupItem key={m.id} value={m.id} className={CLASE_OPCION}>
                {m.nombre}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
      </div>

      <PrediccionChart
        puntos={p.puntos}
        serie={p.serie}
        modelo={p.modelo}
        nombreModelo={p.nombreModelo[p.modelo]}
        finEntrenamiento={p.finEntrenamiento}
        rango={p.rango}
        onCambiarRango={p.setRango}
      />

      <ErrorChart errores={p.errores} nombreModelo={p.nombreModelo[p.modelo]} />

      <TablaMetricas metricas={p.metricasSerie} nombreModelo={p.nombreModelo} modeloSeleccionado={p.modelo} />
    </div>
  )
}
