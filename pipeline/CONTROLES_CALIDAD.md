# Controles de calidad del pipeline

La etapa `02_validacion.py` comprueba los seis controles del ejercicio 3 antes
de preparar la serie o ajustar el modelo. La ingesta comprueba primero que los
archivos puedan leerse y tengan las columnas necesarias.

Un error critico detiene la ejecucion con codigo distinto de cero. Una
advertencia queda registrada y permite continuar. Se reunen todos los controles
que puedan evaluarse, para mostrar los problemas en un mismo reporte.

## Reglas de advertencia y detencion

| Control | Que verifica | Advertencia | Detencion |
|---|---|---|---|
| Columnas y tipos | Columnas indispensables y conversion de anio, mes y llegadas a numeros; anio y mes deben ser enteros | Columnas adicionales no previstas y no utilizadas | Falta una columna indispensable, encabezados repetidos, archivo ilegible o tipo numerico incompatible |
| Fechas y cobertura | Fecha valida, primer dia del mes, coincidencia con anio y mes y cobertura sin residentes | Meses historicos sin cobertura fuera de los periodos necesarios | Fecha invalida o incoherente, fechas diarias o falta un mes de ajuste, evaluacion o referencia |
| Unicidad | Cada combinacion de fecha, via, frontera, pais, tipo y agrupacion de residencia aparece una sola vez | Coincidencias si se omite agrupacion de residencia | Se repite la combinacion completa, incluso entre los dos archivos de origen |
| Faltantes | Distingue campos necesarios de columnas no utilizadas por el procedimiento | Ausencias en columnas opcionales | Falta un valor de fecha, anio, mes, pais, tipo, llegadas, clave completa o procedencia |
| Valores y denominadores | Conteos no negativos y finitos; totales mensuales positivos para el logaritmo | No se permite continuar con valores invalidos. Los ceros por registro se informan sin descartarlos | Conteo negativo o infinito, total mensual no finito o no positivo en los periodos necesarios |
| Regla metodologica | Fuente mensual trazable, categorias de visitantes y exclusion configurada de residentes del pais de destino | No se flexibiliza la regla mediante advertencias | Fuente no mensual, categoria ajena al contrato, exclusion desactivada o huellas/procedencia que no coinciden |

Los ceros en registros individuales son validos si el total del mes es positivo.
Un mes sin registros no se transforma en un cero. Tampoco se completa una suma
con valores inventados cuando faltan conteos.

El procedimiento utiliza MAE y RMSE, por lo que no divide entre las llegadas
observadas como lo haria MAPE. El reporte indica que ese denominador no aplica.
La cobertura comprueba que el conjunto de meses a evaluar no este incompleto.
Si despues se incorpora un calculo con otro denominador, debera agregarse su
validacion antes de utilizarlo.

## Poblacion y cobertura

La cobertura y los totales mensuales se comprueban sobre una vista de turistas
y excursionistas que excluye Pais igual a Guatemala. Esta vista solo se utiliza
para validar. El CSV validado conserva todas las filas y valores de la ingesta.
La etapa de preparacion aplicara el filtro al construir la serie del modelo.

Los meses necesarios se calculan desde `configuracion.toml`. Actualmente son
enero de 2023 a diciembre de 2025 para ajuste, enero a junio de 2026 para
evaluacion y enero a junio de 2025 para la referencia del anio anterior.

En la base actual, abril a agosto de 2020 no tienen registros de visitantes
sin residentes. Como estan fuera de los periodos requeridos, se registran cinco
meses sin cobertura como advertencia. Si el periodo de ajuste se cambiara para
incluirlos, la misma ausencia impediria continuar.

## Las 20 coincidencias parciales

La clave parcial omite Agrupacion Residencia y encuentra 20 registros
adicionales distribuidos en 18 grupos, con 38 filas involucradas. Al incluir
la agrupacion de residencia no quedan duplicados bajo la clave completa.
No se eliminan filas automaticamente. Si se repite tambien la agrupacion de
residencia, el control falla en lugar de decidir que conteo debe conservarse.

La columna `archivo_origen` no forma parte de la clave de unicidad. Un mismo
registro no se considera diferente solo por aparecer en otro archivo.

## Reporte y salidas

Las rutas de salida se definen en la configuracion:

- `data/processed/02_validacion.json` contiene el resultado de cada control,
  errores, advertencias, conteos, ejemplos acotados y periodos evaluados.
- `data/processed/02_validado.csv` se reemplaza solo si no hay fallos criticos.

El reporte distingue `ok`, `advertencia`, `error` y `no_evaluado` por control.
Si una lectura falla durante la ingesta, se registra el problema estructural y
los otros controles quedan como no evaluados. No se inventan resultados.

`apto_para_preparacion` habilita la siguiente etapa. No autoriza publicar.
`publicacion_autorizada` permanece en falso porque la aceptacion predictiva
todavia no se ha implementado. Un fallo deja un reporte rechazado y conserva
el CSV validado anterior, que no debe reutilizarse ignorando ese rechazo.

La validacion comprueba la huella de la ingesta, el manifiesto, las huellas de
los CSV originales y los conteos por archivo de origen. Esto detecta cambios
entre etapas. No sustituye la documentacion institucional del origen mensual
ni constituye una firma digital contra modificaciones deliberadas.

## Ejecucion y pruebas

Desde la raiz del repositorio, con el entorno virtual activado:

```bash
python pipeline/src/run_pipeline.py
python -m unittest discover -s pipeline/tests -v
```

El primer comando ejecuta las etapas disponibles, incluidos preparacion y ajuste.
Para ejecutar solo la validacion
debe existir una ingesta y un manifiesto consistentes:

```bash
python pipeline/src/02_validacion.py
```

Las pruebas usan archivos sinteticos temporales. Incluyen fecha invalida,
mes ausente, duplicado completo, coincidencia parcial valida, faltantes
criticos y opcionales, tipo incompatible, negativo, infinito, total mensual
cero, fuente modificada, categoria no turistica y exclusion desactivada.
Tambien comprueban que las salidas previas y un archivo de publicacion de
prueba permanezcan intactos ante fallos.

Esta evidencia verifica la proteccion de archivos. La consulta de una version
aprobada desde el tablero se demostrara cuando se implemente esa integracion.
