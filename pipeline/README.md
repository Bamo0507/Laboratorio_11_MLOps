# Pipeline de llegadas mensuales a Guatemala

El pipeline se construye por etapas. Actualmente estan disponibles los dos CSV
de entrada, la configuracion, el setup de Python, la ingesta, los seis controles
de calidad y la preparacion de la serie. Todavia no se ejecutan el ajuste,
la evaluacion predictiva ni la publicacion.

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

El orquestador ejecuta ingesta, validacion y preparacion. Para ejecutar solo la ingesta:

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

Las versiones de las dependencias estan fijadas. Los umbrales de aceptacion se
definiran antes de ejecutar la evaluacion. Esta configuracion inicial no
autoriza publicaciones.
