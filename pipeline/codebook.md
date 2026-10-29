# Diccionario de la serie mensual preparada

Documenta `data/processed/03_serie_mensual.csv`, `03_ajuste.csv` y
`03_evaluacion.csv`. Se generan mediante ingesta, validacion y preparacion a
partir de `data/raw/lab1/entrenamiento.csv` y `prueba.csv`, heredados del
laboratorio 1. El origen es la Base de Migracion de enero de 2009 a junio de
2026. Son cifras de uso academico, no oficiales.

## Variables

Los tres CSV comparten el siguiente contrato de columnas.

| Variable | Tipo | Descripcion | Valores y notas |
|---|---|---|---|
| fecha | datetime durante el procesamiento, texto en CSV | Primer dia del mes representado | Formato AAAA-MM-DD y una sola fila por mes |
| viajeros | float, admite NaN en la historia | Suma de llegadas de turistas y excursionistas sin residentes | Conserva decimales del origen. No representa personas unicas |
| registros | int | Cantidad de filas originales seleccionadas que contribuyen al mes | Derivada. Cero indica que no hay registros seleccionados para ese mes |
| conjunto | string | Uso del mes segun la configuracion | ajuste, evaluacion o historico |

`03_ajuste.csv` contiene solo los meses de ajuste, actualmente enero de 2023 a
diciembre de 2025. `03_evaluacion.csv` contiene solo enero a junio de 2026.
Los valores de ambos archivos deben ser observados, finitos y positivos para
el modelo logaritmico. El nombre de los CSV originales no determina estas
particiones nuevas.

## Reglas de preparacion

1. Se exige un reporte de calidad apto con los seis controles evaluados.
2. Las huellas del CSV validado, la ingesta, la configuracion y las fuentes
   deben coincidir con la validacion. Un cambio exige volver a validar.
3. Se seleccionan los tipos de visitante definidos en la configuracion,
   actualmente Turista y Excursionista.
4. Se excluyen los paises de residencia configurados, actualmente Guatemala.
5. Se suman las llegadas por mes, sin redondear las cifras de origen.
6. Se conserva el calendario mensual completo de la fuente y se separan los
   meses de ajuste y evaluacion sin mezclar informacion entre periodos.

Las coincidencias bajo una clave parcial no se eliminan. Si cambia la
agrupacion de residencia, los registros contribuyen a la suma porque son
registros distintos bajo la clave completa validada.

## Faltantes

Abril a agosto de 2020 no tienen registros de la poblacion sin residentes.
`viajeros` queda como NaN, representado por una celda vacia en el CSV. Es una
ausencia en el origen para esta poblacion, no un valor rechazado por invalido.
No se imputa, interpola ni asigna cero. `registros` queda en cero porque no
existen filas seleccionadas para sumar.

No se permiten meses sin cobertura dentro de ajuste, evaluacion o los meses
necesarios para la referencia. Esos casos detienen el pipeline antes de la
preparacion. Un registro individual con cero llegadas se conserva si el total
mensual requerido sigue siendo positivo.

## Separacion temporal

La etapa no calcula promedios ni escalados a partir de la historia completa.
La suma de cada mes depende solo de sus registros. Alterar un valor del tramo
de evaluacion no cambia los valores del archivo de ajuste. El logaritmo y el
entrenamiento se aplicaran en la siguiente etapa, usando el archivo de ajuste.

## Reporte de preparacion

`03_preparacion.json` registra filas seleccionadas y excluidas, cobertura,
periodos, poblacion, archivos generados y sus huellas. La suma de los registros
seleccionados se compara con la suma mensual, usando las tolerancias definidas
en `configuracion.toml`. Son tolerancias de aritmetica de punto flotante, no
permisos para perder o imputar llegadas.

Esta etapa no publica estimaciones ni reemplaza los resultados del tablero.
