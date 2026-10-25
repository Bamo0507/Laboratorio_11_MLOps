/** Línea de fuente común a todos los gráficos: origen, fecha de corte y alcance de las cifras. */
export function PieFuente({ extra }: { extra?: string }) {
  return (
    <p>
      Fuente: Base de Migración, turistas y excursionistas. Datos hasta junio de 2026. Cifras estimadas de uso académico,
      no oficiales.{extra ? ` ${extra}` : ""}
    </p>
  )
}

/** Nota del cambio de fuente de enero de 2023 para los gráficos descriptivos. */
export function NotaQuiebre() {
  return (
    <p>
      No incluye a los residentes en Guatemala: la base los registraba hasta 2022 y desde 2023 ya no, así que se excluyen
      en todo el periodo para comparar el mismo grupo de visitantes.
    </p>
  )
}
