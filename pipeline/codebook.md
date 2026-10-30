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

## Artefactos de ajuste SARIMA

`04_modelo_sarima.pkl` conserva el resultado entrenado, incluidos sus parametros
y el estado necesario para pronosticar sin volver a ajustar. Se genera solo
con `03_ajuste.csv`, que actualmente contiene 36 observaciones. Su escala de
trabajo es el logaritmo de las llegadas.

`04_ajuste.json` documenta el periodo utilizado, configuracion y parametros
aprendidos. En esta estructura SARIMA, `ar.S.L12` es el coeficiente
autorregresivo estacional estimado y `sigma2` es la varianza estimada de las
innovaciones en la escala transformada. Son parametros aprendidos con los datos,
mientras que los ordenes p, d, q, P, D, Q y s se fijan antes del entrenamiento.

Los indicadores AIC, BIC y log-verosimilitud describen el ajuste al entrenamiento.
La precision frente a los seis meses reservados se medira en la etapa de
evaluacion. Este reporte no aprueba una publicacion ni contiene errores de
prediccion calculados con los valores reservados.

## Comparacion fuera de muestra

`05_comparacion.csv` se genera con el modelo ajustado, la serie mensual y los
meses reservados. Todas las cantidades conservan decimales y se expresan en
llegadas por mes.

| Variable | Tipo | Descripcion | Valores validos / notas |
| --- | --- | --- | --- |
| fecha | string | Mes de evaluacion | AAAA-MM-01, enero a junio de 2026 |
| observado | float | Llegadas reportadas en la base academica para el mes | Finito y positivo |
| sarima | float | Exponencial del pronostico logaritmico | Derivada, finita y positiva, sin correccion de sesgo |
| fecha_referencia | string | Mes utilizado por la referencia | Mismo mes del anio anterior, conocido al terminar el ajuste |
| referencia | float | Llegadas observadas en fecha_referencia | Finito y positivo |
| error_sarima | float | Pronostico SARIMA menos observado | Derivada, positivo indica sobreestimacion |
| error_referencia | float | Referencia menos observado | Derivada, positivo indica sobreestimacion |

`05_evaluacion.json` contiene MAE y RMSE de ambos metodos sobre los mismos meses,
la regla configurada, su resultado y las huellas de entradas y salida. No se
permiten faltantes en la comparacion ni se imputan. Superar la regla requiere
errores estrictamente menores en ambas metricas. No autoriza publicaciones.

## Candidato para revision

`06_candidato.json` empaqueta las estimaciones de `05_comparacion.csv` y los
resultados de `05_evaluacion.json`. Conserva la poblacion nacional sin residentes,
las mismas seis fechas y las cantidades sin redondear. No imputa ni transforma
valores y no incorpora proyecciones posteriores a la evaluacion.

| Campo | Tipo | Descripcion | Valores validos / notas |
| --- | --- | --- | --- |
| version_esquema | int | Version del contrato del candidato | 1 |
| tipo | string | Contenido del paquete | estimaciones_evaluadas |
| publicacion_autorizada | bool | Autorizacion de publicacion | Siempre false en esta etapa |
| supera_regla_desempeno | bool | Resultado de la regla previa | Debe coincidir con las metricas |
| estado_desempeno | string | Decision legible | supera_regla o no_supera_regla |
| motivo | string | Explicacion de la decision | Desempeno insuficiente o publicacion pendiente |
| poblacion | object | Destino, unidad y exclusiones | Copia de la configuracion |
| periodo | object | Inicio, fin y cantidad de meses | Copia del periodo evaluado |
| modelo | object | Configuracion del SARIMA | Sin reentrenamiento en esta etapa |
| referencia | object | Metodo de comparacion | Mismo mes del anio anterior |
| regla | object | Criterio previo de desempeno | MAE y RMSE estrictamente menores |
| metricas | object | MAE y RMSE de ambos metodos | Mismas unidades y fechas |
| estimaciones | array | Registros mensuales | Mismas variables que 05_comparacion.csv |
| metodo | string | Forma de generar el horizonte | Origen fijo al cierre del ajuste |
| transformacion_inversa | string | Interpretacion de la exponencial | Sin correccion de sesgo |
| limitacion | string | Alcance de la evaluacion | Seis meses no garantizan desempeno futuro |
| trazabilidad | object | Huellas SHA-256 | Configuracion, comparacion y reporte de evaluacion |

`06_exportacion.json` certifica el estado de la etapa, el numero de estimaciones,
la decision, las huellas de entrada, el codigo y la ruta y huella del candidato.
Si la exportacion se rechaza, el candidato anterior puede seguir en disco.
Solo debe consumirse cuando el reporte este completado y su huella coincida.
El tablero no consume este candidato. Lee una version aprobada que incorpora
los metadatos de publicacion.

## Version aprobada y decision de publicacion

`06_exportacion.json` incluye ahora `id_ejecucion_local` (UUID de la exportacion)
y `fecha_generacion` (fecha y hora UTC con zona horaria). Es un identificador
local y se conserva junto con `id_ejecucion_mlflow` cuando ejecuta el orquestador.

`07_publicacion.json` registra el estado `publicado`, `no_publicado` o
`rechazado`. Cuando la decision puede completarse incluye el identificador local,
las huellas del candidato y del reporte de exportacion, la version anterior,
la version vigente, el motivo y si hay estimaciones aprobadas disponibles.
Un rechazo por error incluye su causa y no autoriza publicaciones.

`publicaciones/vigente.json` contiene `version`, `archivo`, `sha256` y
`fecha_generacion`. La ruta es relativa a `publicaciones` y apunta a una version
en `versiones/`. La huella debe coincidir antes de consumir sus valores.

Cada version aprobada conserva el contenido del candidato y agrega `version`,
`id_ejecucion_local`, `tipo_identificador` y `fecha_generacion`. Su autorizacion
es `true`. El motivo indica que supero calidad, integridad y desempeno.
Cada registro mensual incorpora los siguientes campos adicionales.

| Campo | Tipo | Descripcion | Valores validos / notas |
| --- | --- | --- | --- |
| destino | string | Destino de las llegadas | Guatemala |
| unidad | string | Unidad del valor estimado | llegadas_por_mes |
| valor | float | Estimacion autorizada | Igual al pronostico SARIMA certificado |
| version_procedimiento | string | Version que conserva configuracion y trazabilidad | SHA-256 de la version |
| id_ejecucion_local | string | Identificador de la exportacion que produjo el candidato | UUID local, adicional al identificador de MLflow |
| fecha_generacion | string | Momento de generacion de la exportacion | ISO 8601 en UTC |

No se cambia la poblacion ni se imputan, redondean o recalculan estimaciones.
Una version rechazada por desempeno no genera una version aprobada. Si nunca
hubo una aprobacion, no existe el indicador y no hay estimaciones aprobadas
para consultar. Los JSON heredados del tablero no se consideran automaticamente
versiones aprobadas de este pipeline.

## Identificacion en MLflow

`06_exportacion.json` y `07_publicacion.json` incorporan `id_ejecucion_mlflow`
cuando interviene el orquestador. La version publicada y cada registro mensual
conservan el mismo campo. En una exportacion individual sin run su valor es
nulo y no se inventa una ejecucion. Los identificadores locales siguen siendo
validos como referencia de la exportacion.

`evidencia_mlflow.json` identifica dos corridas completas, sus tolerancias y las
diferencias observadas. Tambien contiene un fallo controlado y la consulta de
los parametros, metricas, etiquetas y archivos de los tres runs. Los valores
predictivos del run que fallo antes de evaluar no se completan con ceros ni
con metricas de una corrida anterior. Su conjunto de metricas queda vacio.

## Protocolo y decision de aceptacion

La evaluacion incorpora los siguientes campos en `05_evaluacion.json`.

| Campo | Tipo | Descripcion |
| --- | --- | --- |
| protocolo_temporal | object | Ultimo mes utilizado para ajustar, cantidad de observaciones de ajuste, meses ocultos, horizontes y meses de referencia |
| comparabilidad | object | Comparabilidad interna de los valores academicos y limitaciones para reconstruir la informacion historica |
| diagnostico | object | Sesgo medio, meses sobreestimados o subestimados y cantidad de meses con menor error por metodo |
| diagnostico.aumento_relativo_error_frente_referencia | object | Comparacion de MAE y RMSE agregados. No es MAPE. Se informa null si el error de referencia es cero |

La comparabilidad declarada debe ser verdadera antes de calcular errores. No
se calculan errores para meses sin observaciones comparables ni se rellenan
sus metricas con cero. La ausencia historica de datos o revisiones no se
interpreta como evidencia de disponibilidad en tiempo real.

`07_publicacion.json` incluye `criterios_aceptacion` al completar la decision.
Contiene `calidad`, `integridad`, `observaciones_comparables` y `desempeno`.
Calidad e integridad solo se marcan como verificadas despues de comprobar los
certificados y el contenido del candidato. Si falla una verificacion antes de
la decision, el reporte se rechaza sin inventar estos resultados.

El candidato y cualquier version aprobada conservan tambien `protocolo_temporal`,
`comparabilidad` y `diagnostico`. La etapa de publicacion exige que coincidan con
el reporte de evaluacion certificado. Estas descripciones no se descartan al
empaquetar el resultado para el tablero.

## Contrato para el tablero

La version aprobada y cada fila de `estimaciones` incluyen `id_ejecucion`,
ademas de `id_ejecucion_local` e `id_ejecucion_mlflow`. Se utiliza el ID de MLflow
si el orquestador registro la exportacion y, en caso contrario, el ID local.
`tipo_identificador` distingue ambos casos. No se inventa un run para una
publicacion individual.

El archivo aprobado conserva por fila `destino`, `fecha`, `valor`, `unidad`,
`id_ejecucion`, `fecha_generacion` y `version_procedimiento`. El periodo global
se conserva en `periodo`. La fecha mensual usa AAAA-MM-01, la fecha de generacion
incluye zona horaria y la unidad es llegadas_por_mes.

El servidor de Next.js verifica estos campos, la aprobacion, las huellas, la
cobertura y la correspondencia de las metricas. Solo envia al navegador destino,
fecha de generacion, periodo, MAE y RMSE y los pares observado-estimado por mes.
Los detalles del procedimiento permanecen en el archivo aprobado y en MLflow.
Las cantidades se redondean unicamente al mostrarlas, sin modificar el archivo.
