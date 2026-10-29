# Pipeline de llegadas mensuales a Guatemala

El pipeline se construye por etapas. Actualmente estan disponibles los dos CSV
de entrada, la configuracion, el setup de Python, la ingesta, los seis controles
de calidad, la preparacion de la serie, el ajuste SARIMA y la evaluacion
predictiva. El registro en MLflow y la publicacion siguen pendientes.

## Datos de entrada

`data/raw/lab1/entrenamiento.csv` y `prueba.csv` son copias intactas de los
insumos del laboratorio 10, heredados del laboratorio 1. Se incluyen en este
repositorio privado para que cada integrante disponga de los mismos archivos.
Los scripts no deben modificarlos. Los resultados se escribiran en
`data/processed/`, que queda fuera de Git.

## Configuracion portable

`configuracion.toml` contiene rutas, periodos, poblacion, parametros del SARIMA,
referencia y nombres de columnas. Para cambiar las fechas de ajuste se edita
este archivo, sin modificar la logica del modelo.

Las rutas son relativas a la carpeta que contiene la configuracion. No se
utilizan rutas personales, carpetas de otros laboratorios ni el directorio
desde el que se invoca Python. `src/config.py` calcula las rutas completas al
ejecutarse y rechaza rutas absolutas o rutas que salgan de esta carpeta.

## Comprobar este primer paso

Se utiliza Python 3.13. `src/00_init.py` crea `.venv/` e instala las versiones de
`requirements.txt`, incluidas las dependencias indirectas. `requirements.in`
identifica las dependencias directas. La instalacion para macOS, Linux y Windows
esta documentada en el README de la raiz.
Desde la raiz del repositorio:

```bash
python3.13 pipeline/src/00_init.py
source pipeline/.venv/bin/activate
python pipeline/src/config.py
```

En Windows se puede usar `py -3` en lugar de `python3`.
La salida muestra la configuracion y las rutas resueltas en esa computadora.
Ver una ruta completa en la salida es normal. Se calcula durante la ejecucion,
no esta escrita en los scripts ni en el TOML.

Esta comprobacion solo lee la configuracion. No entrena modelos.

## Etapa 1 implementada

Con el entorno activado, desde la raiz del repositorio:

```bash
python pipeline/src/run_pipeline.py
```

El orquestador ejecuta ingesta, validacion, preparacion y ajuste. Para ejecutar solo la ingesta:

```bash
python pipeline/src/01_ingesta.py
```

Ambos comandos aceptan `--config` para indicar otro archivo de configuracion.

```text
data/raw/lab1/entrenamiento.csv + prueba.csv
  -> src/01_ingesta.py
  -> data/processed/01_ingesta.csv
  -> data/processed/01_ingesta.json
```

| Etapa | Responsabilidad | Entrada | Salida |
|---|---|---|---|
| 01_ingesta.py | Leer y unir sin transformar valores | Los dos CSV originales | CSV reunido y reporte JSON |

La lectura conserva los valores como texto, incluidos vacios, ceros iniciales y
marcadores como `NA` o `NaN`. No elimina filas, filtra residentes, convierte
fechas ni suma llegadas. Esa separacion permite revisar la fuente antes de
aplicar cada transformacion.

`archivo_origen` identifica la procedencia de cada fila. Los nombres historicos
entrenamiento y prueba no definen la particion de este laboratorio. La nueva
division se construira despues con los periodos de `configuracion.toml`.

Se comprueba que los archivos existan, tengan registros y columnas indispensables,
no repitan encabezados y compartan las mismas columnas. Una lectura fallida no
reemplaza el CSV de ingesta anterior y genera un reporte de calidad bloqueado.
Estas comprobaciones estructurales preceden a los seis controles de la etapa 2.

El reporte guarda la huella SHA-256 de los mismos bytes utilizados para leer
cada CSV, su tamano, columnas y filas. La huella permite identificar si el
contenido del archivo cambio. Los archivos de salida se escriben primero en
un temporal y se reemplazan al terminar, para evitar un CSV parcialmente escrito.

## Etapa 2 implementada

```text
01_ingesta.csv + 01_ingesta.json + fuentes originales
  -> src/02_validacion.py
  -> data/processed/02_validacion.json
  -> data/processed/02_validado.csv, solo si no hay errores criticos
```

| Etapa | Responsabilidad | Entrada | Salida |
|---|---|---|---|
| 02_validacion.py | Comprobar seis controles y trazabilidad | Ingesta, manifiesto y fuentes | Reporte de calidad y CSV validado |

Las reglas detalladas y los casos que advierten o detienen la ejecucion estan en
[CONTROLES_CALIDAD.md](CONTROLES_CALIDAD.md). La validacion no modifica datos
originales, no imputa faltantes ni elimina coincidencias parciales. Un fallo
critico conserva el CSV validado anterior y escribe un reporte rechazado.
Las etapas siguientes deberan exigir un reporte apto y verificar su huella
antes de consumir ese CSV. La validacion no autoriza la publicacion.

Con el entorno activado se puede ejecutar solo esta etapa o las pruebas:

```bash
python pipeline/src/02_validacion.py
python -m unittest discover -s pipeline/tests -v
```

## Etapa 3 implementada

```text
02_validado.csv + 02_validacion.json
  -> src/03_preparacion.py
  -> 03_serie_mensual.csv
  -> 03_ajuste.csv + 03_evaluacion.csv
  -> 03_preparacion.json
```

| Etapa | Responsabilidad | Entrada | Salida |
|---|---|---|---|
| 03_preparacion.py | Construir la serie sin residentes y separar periodos | Datos y reporte de calidad vigentes | Serie mensual, ajuste, evaluacion y reporte |

Se seleccionan los tipos de visitante configurados y se excluyen residentes
antes de sumar llegadas por mes. Los meses sin cobertura quedan sin dato y las
cifras no se redondean. El reporte registra las filas excluidas, los periodos y
las huellas de las salidas. Ver [codebook.md](codebook.md) para el diccionario.

Antes de continuar, se exige un reporte apto y las huellas vigentes del CSV
validado, las fuentes originales, la ingesta y la configuracion. Si cambia
alguno, hay que repetir las etapas previas. Ante un rechazo se conservan los
CSV preparados anteriores y se registra un reporte de preparacion rechazado.

Para ejecutar solo esta etapa, con el entorno activado:

```bash
python pipeline/src/03_preparacion.py
```

Con la configuracion actual, el archivo de ajuste contiene 36 meses y el de
evaluacion contiene seis. Las pruebas comprueban que modificar observaciones
de evaluacion no altere el archivo de ajuste y que una copia en otra ubicacion
produzca las mismas salidas.

## Etapa 4 implementada

```text
03_ajuste.csv + reportes vigentes
  -> src/04_ajuste.py
  -> 04_modelo_sarima.pkl
  -> 04_ajuste.json
```

| Etapa | Responsabilidad | Entrada | Salida |
|---|---|---|---|
| 04_ajuste.py | Ajustar y guardar SARIMA con entrenamiento | Serie de ajuste y certificados vigentes | Modelo y reporte de ajuste |

La etapa aplica el logaritmo a las llegadas del archivo de ajuste y utiliza
los ordenes SARIMA definidos en la configuracion. No abre el CSV de evaluacion
ni usa esas observaciones para estimar o seleccionar parametros. Si se cambia
un insumo o la configuracion, primero deben repetirse las etapas previas.

El modelo se guarda solo si converge y sus parametros e indicadores son finitos.
Antes de reemplazar un modelo anterior, se vuelve a cargar el archivo nuevo y
se exige igualdad exacta de parametros y del pronostico de comprobacion de un
mes. Este pronostico interno solo comprueba la persistencia y no se compara
con observaciones reservadas ni se publica.

El reporte registra AIC, BIC y log-verosimilitud del ajuste. No son el MAE ni el
RMSE de evaluacion. Tambien conserva las advertencias sin ocultarlas, las
versiones de Python y librerias, el commit disponible, si hay cambios locales
y las huellas de los scripts. Un fallo deja un reporte rechazado y conserva
el archivo del modelo anterior.

### Opciones del ajuste

| Opcion en configuracion.toml | Uso |
|---|---|
| orden y orden_estacional | Estructura SARIMA acordada |
| transformacion | Logaritmo de llegadas |
| tendencia | n significa que no se agrega una tendencia deterministica |
| exigir_estacionariedad | Restringe la parte autorregresiva a parametros estacionarios |
| exigir_invertibilidad | Restringe la parte de media movil a parametros invertibles |
| metodo_optimizacion | L-BFGS, utilizado para estimar los parametros |
| iteraciones_maximas | Limite de iteraciones del optimizador, actualmente 200 |

Estas restricciones se aplican al modelo transformado y diferenciado, no
significan que la serie original de llegadas tenga nivel constante. El ajuste
utilizado no realiza muestreo ni inicializacion aleatoria, por lo que no
necesita semilla. Las pruebas sinteticas si fijan una semilla para generar sus
propios datos de prueba.

Para ejecutar solo esta etapa, con el entorno activado:

```bash
python pipeline/src/04_ajuste.py
```

Las pruebas comprueban recuperacion, repetibilidad numerica, independencia
respecto de los valores de evaluacion y conservacion del modelo anterior ante
fallos de convergencia o de escritura/recuperacion. La igualdad numerica no
implica exigir archivos pickle identicos entre plataformas o versiones.

Referencias de implementacion de statsmodels:
[ajuste SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.fit.html)
y [persistencia del modelo](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.save.html).

## Etapas previstas

```text
CSV de entrada + configuracion
  -> lectura
  -> validacion de datos
  -> preparacion mensual
  -> ajuste SARIMA
  -> evaluacion contra referencia
  -> generacion de estimaciones candidatas
  -> publicacion de la version aprobada
```

Cada etapa tendra su propio script y salida para poder revisar que ocurrio
antes de avanzar. El orquestador las ejecutara con un comando y se detendra
ante un fallo. MLflow registrara la ejecucion y sus archivos.

Las versiones de las dependencias estan fijadas. La regla de desempeno se
configura antes de ejecutar la evaluacion. Ninguna etapa actual autoriza
publicaciones.

## Etapa 5 de evaluacion

```text
04_modelo_sarima.pkl + 03_evaluacion.csv + 03_serie_mensual.csv + certificados
  -> 05_evaluacion.py
  -> 05_comparacion.csv + 05_evaluacion.json
```

| Etapa | Archivo | Responsabilidad | Entrada | Salida |
| --- | --- | --- | --- | --- |
| 5 | 05_evaluacion.py | Comparar errores con la referencia y aplicar la regla previa | Modelo, series y reportes vigentes | Comparacion mensual y reporte de desempeno |

```bash
python pipeline/src/05_evaluacion.py
```

El pipeline completo tambien ejecuta esta etapa. Si cambia la configuracion,
se deben regenerar las etapas anteriores para que sus certificados coincidan.

Se genera un pronostico de origen fijo desde diciembre de 2025 hasta junio de
2026. No se reentrena ni se incorporan llegadas reales de 2026 entre pasos.
La exponencial devuelve el pronostico logaritmico a llegadas, sin redondeo ni
factor de reparto. Sin correccion de sesgo, este valor representa una mediana
condicional y no la media aritmetica esperada.

La referencia toma enero de 2025 para enero de 2026, febrero de 2025 para febrero
de 2026, y asi sucesivamente. Ambos metodos se comparan contra las mismas seis
observaciones, en llegadas por mes. MAE es el promedio de los errores absolutos.
RMSE es la raiz del promedio de los errores al cuadrado y da mas peso a los
meses con errores grandes.

Antes de calcular errores se fijo `mae_y_rmse_estrictamente_menores` en la
configuracion. SARIMA supera la regla solo si mejora ambas metricas. Los
empates no pasan, incluso cuando la referencia tiene error cero. La regla no
se cambia a partir de los resultados observados. Una comparacion de seis meses
no demuestra que la mejora se mantenga en el futuro.

Un resultado desfavorable completa la evaluacion con
`supera_regla_desempeno = false`. Un archivo alterado o un error de calculo
rechaza la ejecucion, conserva el CSV anterior y escribe un reporte rechazado.
Los consumidores deben exigir reporte completado y huella del CSV coincidente.
`publicacion_autorizada` permanece en `false`, incluso si se supera la regla.
MLflow y el mecanismo de publicacion todavia no estan implementados.

La generacion del horizonte utiliza
[get_forecast de statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.get_forecast.html).
