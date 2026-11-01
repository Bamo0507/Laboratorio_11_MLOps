# Monitoreo y recuperacion

El pipeline deja un registro de cada ejecucion, revisa sus resultados despues
de publicar y permite volver a una version aprobada anterior. Las alertas del
monitoreo piden revision. No bloquean ni revierten una publicacion. Lo que
detiene el flujo siguen siendo los controles de calidad y la regla de aceptacion.

## 7.1 Registro por ejecucion

`orquestacion.py` escribe `data/processed/registros/<fecha UTC>_<run>.json` al
terminar, tanto si la ejecucion se completa como si se detiene. La misma copia
queda en MLflow como `ejecucion/registro.json`.

| Campo | Contenido |
| --- | --- |
| id_ejecucion, tipo_ejecucion | Run de MLflow y tipo de corrida |
| inicio_utc, fin_utc | Horas de inicio y finalizacion |
| etapas | Inicio, fin y estado de cada etapa intentada |
| etapas_completadas | Etapas terminadas correctamente |
| advertencias | Advertencias de calidad, del ajuste y alertas del monitoreo |
| errores | Linea `[FALLO]` de la etapa que detuvo el flujo |
| publicacion | Decision de la etapa 7, motivo y version vigente al terminar |

Si el flujo se detiene antes de la etapa 7, la publicacion queda como
`no_evaluada` y se informa la version que sigue vigente.

## 7.2 Verificaciones de monitoreo

`08_monitoreo.py` es la ultima etapa del orquestador y tambien puede ejecutarse
por separado. Escribe `data/processed/08_monitoreo.json` y registra en MLflow las
etiquetas `monitoreo.estado`, `monitoreo.actualizacion`, `monitoreo.calidad` y
`monitoreo.resultados`.

| Verificacion | Que revisa | Genera alerta cuando |
| --- | --- | --- |
| Actualizacion | Ultimo mes de las fuentes, huellas frente a la ultima ingesta, fin del candidato y de la version vigente | Las fuentes no llegan a `fin_evaluacion` o tienen meses posteriores, cambiaron despues de procesarse, el candidato o la version vigente terminan en otro mes, o no hay version aprobada |
| Calidad | Filas, faltantes, duplicados completos, coincidencias parciales y meses sin cobertura del reporte 02 | Bajan las filas o sube cualquiera de los otros indicadores frente al monitoreo anterior |
| Resultados | Estimaciones del candidato | Hay valores negativos o no finitos, o la variacion frente al mismo mes del anio anterior supera el umbral |

La primera ejecucion monitoreada queda como referencia de calidad. Una base
historica no deberia perder filas ni ganar faltantes, duplicados o meses sin
cobertura al recibir meses nuevos. Por eso cualquier aumento genera alerta.

El umbral de variacion es `monitoreo.variacion_interanual_maxima = 0.30`. En la
serie real, el percentil 95 de la variacion interanual absoluta fue 0.27 entre
2012 y 2019 y 0.33 entre 2024 y 2025. Una variacion mayor es poco frecuente en
anios sin choques, pero puede ser real. Por eso solo pide revision y no
demuestra por si sola una perdida de precision.

El reporte incluye `error_predictivo` solo si la evaluacion se completo con
observaciones comparables. En otro caso queda en `null`. El monitoreo no
calcula errores nuevos.

Con los datos reales el monitoreo da `con_alertas` por una sola razon: no hay
una version aprobada. Calidad no tiene cambios frente a la referencia. Las
estimaciones SARIMA varian entre -5.2 % y +15.3 % frente a 2025, bajo el umbral.

## 7.3 Prueba controlada

```bash
python pipeline/src/evidencia_recuperacion.py
```

SARIMA no supera la referencia con los datos reales y la regla no se cambia.
Por eso la prueba usa datos sinteticos con semilla fija en
`data/processed/demo_recuperacion/`, con su propia configuracion y sus propias
publicaciones. Esa configuracion declara `datos_sinteticos = true`, que queda en
cada version y hace que el tablero muestre la advertencia de prueba. Los runs se
registran en el experimento principal con `tipo_ejecucion` que empieza con
`recuperacion_`.

| Paso | Accion | Resultado comprobado |
| --- | --- | --- |
| 1 | Serie con crecimiento de 1.2 % mensual | Version A aprobada y vigente, monitoreo sin alertas de calidad ni resultados |
| 2 | Crecimiento de 3 % mensual y un mes dividido en dos agrupaciones | Version B aprobada. Alertas de calidad, coincidencias parciales de 0 a 1, y de variacion interanual sobre 30 % |
| 3 | Fila duplicada bajo la clave completa | La validacion detiene el flujo. El run queda `FAILED`, publicacion `no_evaluada`, B sigue vigente |
| 4 | Se quita el duplicado y se ejecuta otra vez | Version C aprobada con las mismas estimaciones de B |
| 5 | `restaurar` con el prefijo de A | A vuelve a estar vigente. A, B y C siguen guardadas |

El script verifica cada paso y se detiene si alguno no se cumple. Tambien
comprueba que los CSV originales y `publicaciones/vigente.json` reales no
cambien. La evidencia queda en `data/processed/evidencia_recuperacion.json`, con
los registros de las cuatro ejecuciones y el indicador restaurado.

Las metricas varian levemente entre plataformas. El MAE de A fue 21 113 en
macOS y 21 116 en el contenedor Linux. Con ruido sintetico muy bajo el
optimizador no converge en algunas plataformas. Las combinaciones elegidas
convergieron en macOS arm64 y en el contenedor Linux arm64.

## 7.4 Restaurar una version aprobada

Las versiones aprobadas no se borran ni se sobrescriben. Para ver las guardadas
y cual esta vigente:

```bash
python pipeline/src/restaurar.py --listar
```

Para reactivar una:

```bash
python pipeline/src/restaurar.py --version <identificador o prefijo>
```

El comando toma el bloqueo de publicacion, verifica que el archivo corresponda
a su nombre y este aprobado, y reemplaza `vigente.json` de forma atomica. El
indicador agrega `restaurada_utc` y `version_reemplazada`. Si la version no
existe, el prefijo es ambiguo o el archivo no esta aprobado, no cambia nada.

El tablero lee `vigente.json` en cada solicitud. Para ver la version restaurada
basta recargar Pronosticos o pulsar Consultar actualizacion. Para consultar la
prueba sintetica:

```bash
TURISMO_PUBLICACIONES_DIR=pipeline/data/processed/demo_recuperacion/data/processed/publicaciones pnpm start
```

Se comprobo en el navegador que el tablero mostro A con la advertencia de datos
sinteticos y, despues de restaurar C y consultar la actualizacion, el MAE de C.
Los comandos equivalentes con Docker estan en el README de la raiz.

## Pruebas

`tests/test_recuperacion.py` comprueba las alertas de resultados y calidad, el
monitoreo sobre una version aprobada, la restauracion de la version anterior y
el rechazo de una version alterada o de un prefijo invalido sin cambiar el
indicador. `tests/test_ciclo_pipeline.py` comprueba un registro completado con
monitoreo y otro fallido con su causa.

```bash
python -m unittest discover -s pipeline/tests -v
```
