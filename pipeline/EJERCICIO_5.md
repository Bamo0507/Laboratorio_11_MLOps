# Evaluacion temporal y regla de aceptacion

Se utiliza la evaluacion implementada en `05_evaluacion.py` y la decision de
publicacion de `07_publicacion.py`. Se conserva el modelo SARIMA
(0,1,0)(1,1,0,12) en logaritmos y la regla definida antes de la primera evaluacion.
No se ajustan hiperparametros ni umbrales para aprobar el resultado obtenido.

## 5.1 Meses ocultos y orden temporal

Se reservan enero a junio de 2026. Sus valores no se utilizan para estimar los
parametros del modelo. SARIMA recibe unicamente los 36 totales mensuales de
enero de 2023 a diciembre de 2025, transformados mediante el logaritmo.

La funcion `pronosticar` recibe el modelo ajustado y las fechas que debe
estimar. No recibe los valores reservados. Genera los seis meses desde un
unico corte en diciembre de 2025. Enero es un paso hacia adelante y junio es
el sexto. No se incorpora el valor observado de enero para pronosticar febrero,
ni los meses posteriores para actualizar los parametros.

El reporte `05_evaluacion.json` identifica el ultimo mes utilizado, las 36
observaciones de ajuste, los seis meses ocultos y los meses de referencia.
Se verifica que las fechas y los valores guardados en el modelo coincidan
con el conjunto de ajuste. Todos los meses pronosticados deben ser posteriores
al ultimo mes utilizado para ajustar.

Las pruebas cambian los valores reservados a una cantidad muy distinta,
regeneran los datos y repiten el ajuste y la evaluacion. Los pronosticos y la
referencia permanecen iguales, mientras los errores cambian al compararse
con las nuevas observaciones. Esto comprueba que los valores ocultos intervienen
al medir el error y no al construir la prediccion.

### Alcance para enero y febrero de 2026

Se puede realizar una evaluacion retrospectiva con los valores reportados en
la base academica consolidada. La serie y la referencia utilizan la misma
seleccion de turistas y excursionistas, excluyen residentes y representan
llegadas mensuales a nivel nacional. El ajuste y la referencia quedan dentro
del tramo posterior al cambio de fuente de 2023.

Esto permite una comparacion interna del ejercicio, pero no reconstruye
exactamente la informacion disponible en enero y febrero de 2026. No se
conservan versiones historicas de la base para esas fechas, un calendario de
publicacion ni el historial de revisiones de cada dato. Por eso no se puede
asegurar que todos los datos de diciembre de 2025 ya estuvieran disponibles al
comenzar enero, ni que los valores actuales coincidan con los publicados en
ese momento.

Las cantidades son estimaciones expandidas de uso academico y no se presentan
como cifras oficiales. Los errores se interpretan respecto de esos valores
reportados. No se contrastan con un conteo institucional independiente ni se
afirma haber reproducido una prediccion emitida en tiempo real.

`evaluacion.observaciones_comparables` declara si los valores disponibles
permiten esa comparacion interna. Se mantiene en `true` para esta base y debe
cambiarse a `false` si faltan observaciones comparables o cambia su definicion.
La declaracion no reemplaza la revision de procedencia ni convierte cifras
academicas en datos oficiales. El reporte distingue expresamente comparabilidad
interna de disponibilidad historica.

## 5.2 Metricas

MAE es el promedio de las diferencias absolutas entre estimacion y observacion.
Por ejemplo, un MAE de 22 746,68 significa un error absoluto promedio de esa
cantidad de llegadas por mes dentro de los seis meses evaluados.

RMSE es la raiz del promedio de las diferencias al cuadrado. Conserva la unidad
de llegadas y da mas peso a los errores grandes. Se calculan ambas metricas
sobre la escala original, despues de aplicar la exponencial al pronostico
logaritmico, sin redondear ni aplicar un factor de reparto.

No se utiliza MAPE. MAE y RMSE no dividen entre las llegadas observadas, por lo
que no requieren una correccion de porcentajes cuando ese valor es cero.
El contrato actual del pipeline exige totales mensuales positivos en los
periodos necesarios. Si aparece un total que no cumple ese contrato, se
requiere revisar el dato y la metodologia antes de continuar, sin sustituirlo
por una cantidad artificial.

La exponencial directa no aplica una correccion de sesgo. El pronostico se
interpreta como mediana condicional bajo la distribucion logaritmica del modelo,
no como la media aritmetica esperada. Se conserva esta decision metodologica
sin cambiarla a partir del error del conjunto reservado.

## 5.3 Referencia sobre los mismos meses

La referencia utiliza el mismo mes del anio anterior. Enero de 2026 se estima
con enero de 2025, febrero con febrero de 2025, y asi hasta junio. Todos esos
meses son anteriores al corte del ajuste. Este metodo sencillo conserva el
patron anual sin estimar los parametros de SARIMA.

Los dos metodos se comparan con las mismas seis observaciones, la misma
poblacion nacional sin residentes y la misma unidad. No se elimina un mes solo
porque un metodo tenga mas error en el. `05_comparacion.csv` conserva la fecha,
el valor observado, ambos pronosticos, el mes de referencia y ambos errores.

## 5.4 Regla de aceptacion y justificacion

La publicacion exige que se cumplan simultaneamente los siguientes criterios.

| Criterio | Condicion requerida | Justificacion |
| --- | --- | --- |
| Calidad | Los seis controles deben quedar en ok o advertencia, sin errores criticos | No se estima ni publica a partir de datos que incumplen el contrato |
| Cobertura y campos | Cero meses requeridos ausentes y cero valores indispensables faltantes | No se inventan valores ni se comparan conjuntos distintos |
| Unicidad y valores | Cero duplicados completos, conteos invalidos o valores no finitos | Evita inflar las llegadas o producir calculos invalidos |
| Integridad | Coincidencia de las huellas de fuentes, configuracion, modelo, reportes y candidato, con todas las fechas y campos esperados | Garantiza que se publique la misma version que fue validada y evaluada |
| Comparabilidad | Valores observados declarados comparables, ademas de cobertura y poblacion consistentes | Un error solo es interpretable si estimacion y observacion representan la misma variable |
| Desempeno | MAE de SARIMA menor que el MAE de referencia y RMSE de SARIMA menor que el RMSE de referencia | El modelo debe aportar una mejora frente a un procedimiento sencillo en ambas medidas |

El umbral de desempeno es relativo a la referencia. No se establece una cifra
absoluta de llegadas aceptables porque no se dispone de un costo de error
acordado con un usuario del observatorio. Una cifra fija podria ser demasiado
permisiva para meses de menor volumen o demasiado restrictiva para otros.
La comparacion con la referencia utiliza la escala de los mismos meses.

Se exige una mejora estricta en ambas metricas y se rechazan empates. No se
agrega un margen porcentual elegido despues de ver los resultados. Si la
referencia tiene error cero, el modelo no puede superarla bajo esta regla y
la candidata no se aprueba. Las tolerancias de coma flotante usadas para
reproducibilidad o serializacion no se utilizan para convertir un empate
de desempeno en una aprobacion.

Las coincidencias parciales al omitir la agrupacion de residencia y los meses
sin cobertura fuera de los periodos necesarios son advertencias documentadas.
No se confunden con duplicados completos ni con meses faltantes del ajuste o
la evaluacion. Esta distincion permite conservar registros validos sin
flexibilizar los controles criticos.

Seis meses permiten una comparacion acotada. La regla no demuestra significancia
estadistica ni una mejora garantizada en meses futuros. Un cambio posterior de
modelo o criterio debe tratarse como una nueva decision y validarse con otros
periodos reservados. No se utiliza este conjunto para ajustar sucesivamente
el modelo hasta aprobarlo.

## 5.5 Resultado y aplicacion de la regla

| Metrica en llegadas | SARIMA | Mismo mes del anio anterior |
| --- | --- | --- |
| MAE | 22 746,68 | 15 972,69 |
| RMSE | 25 005,99 | 19 392,25 |

SARIMA tiene mas error que la referencia en ambas metricas. En los seis meses
sobreestima las llegadas. Solo obtiene un error absoluto menor que la
referencia en enero y abril. En los otros cuatro meses, la referencia queda
mas cerca del valor reportado. Esta comparacion describe el resultado, sin
atribuirlo a una causa que no se haya probado.

La candidata supera calidad, integridad y comparabilidad interna, pero no
supera desempeno. `07_publicacion.json` registra estos criterios y termina como
`no_publicado`. No se activa una version ni se modifica la regla para aprobar
SARIMA. Si hubiera una version aprobada anterior, seguiria vigente.

Cuando `observaciones_comparables` es `false`, la evaluacion se detiene antes
de calcular errores, deja un reporte rechazado sin metricas nuevas y no
reemplaza la comparacion anterior. El orquestador no registra metricas de
esa evaluacion en MLflow. Tampoco puede reutilizar un reporte rechazado
para exportar o publicar. Esto incluye enero y febrero de 2026 cuando no
existan valores observados comparables para esos meses.

## Ejecucion y evidencia

Desde la raiz del repositorio, con el entorno de Python activado:

```bash
python pipeline/src/run_pipeline.py
python -m unittest discover -s pipeline/tests -v
```

El pipeline genera `05_comparacion.csv`, `05_evaluacion.json` y
`07_publicacion.json` en `pipeline/data/processed`. La evaluacion incluye el
protocolo temporal, la comparabilidad y un diagnostico de sobreestimacion y
error frente a la referencia. La decision de publicacion incluye los criterios
individuales. Estos archivos tambien se conservan en el run de MLflow.

Las pruebas comprueban el aislamiento temporal, las formulas, la referencia,
los empates, el error cero de la referencia, la ausencia de observaciones
comparables y la conservacion de versiones ante errores de calidad o integridad.

## Evidencia de la ejecucion actual

La evaluacion completa quedo registrada en MLflow con el identificador
`35d0c8b50af6433ba74023447c7ef10b`. El run termino como FINISHED y la publicacion
quedo como no_publicado. Sus archivos incluyen el protocolo temporal, el
diagnostico y los criterios de aceptacion. Los datos originales permanecen
intactos.

| Mes de 2026 | Valor reportado | SARIMA | Mismo mes de 2025 |
| --- | --- | --- | --- |
| Enero | 300 664,08 | 310 543,30 | 289 543,60 |
| Febrero | 236 844,11 | 277 796,11 | 254 428,89 |
| Marzo | 291 160,37 | 321 028,16 | 278 538,25 |
| Abril | 260 951,05 | 284 767,35 | 300 287,69 |
| Mayo | 241 312,30 | 259 159,98 | 247 981,93 |
| Junio | 245 687,58 | 259 804,64 | 254 190,10 |

Se muestran dos decimales para lectura. Las metricas y la decision utilizan
los valores completos, sin este redondeo. Son comparaciones retrospectivas
internas de la base academica y no errores frente a cifras oficiales.

La suite completa termino con 69 pruebas aprobadas.
