# Laboratorio 11 de MLOps

Este proyecto continua el tablero del laboratorio 10 sobre llegadas de turistas
y excursionistas a Guatemala. El laboratorio 11 incorpora un pipeline de Python
para preparar datos, ejecutar SARIMA, evaluar sus predicciones y publicar
resultados aprobados con trazabilidad en MLflow.

## Estado actual

El tablero heredado esta en `src/`. En `pipeline/` ya estan los CSV originales,
la configuracion portable, el entorno, la ingesta, los seis controles de calidad,
la preparacion de la serie mensual, el ajuste SARIMA y su evaluacion contra
el mismo mes del anio anterior, ademas de la exportacion de un candidato para
revision y la decision de publicacion controlada. MLflow ya registra el inicio, las etapas y el cierre de cada ejecucion. Se registran tambien codigo, fuentes, parametros, controles, metricas y archivos.
La lectura de versiones aprobadas desde el tablero sigue pendiente.
Actualmente el tablero sigue consultando los JSON del laboratorio 10.

## Estructura

```text
src/                            Tablero Next.js y datos del laboratorio 10
pipeline/
  configuracion.toml            Rutas, periodos y parametros
  requirements.in               Dependencias directas
  requirements.txt              Versiones fijadas, incluidas las indirectas
  .python-version               Version de Python elegida
  src/
    00_init.py                  Preparacion del entorno virtual
    config.py                   Lectura y validacion de configuracion
    01_ingesta.py               Lectura y union de los CSV originales
    02_validacion.py            Ejecucion de los seis controles de calidad
    validacion.py               Reglas de cada control y estructura del reporte
    03_preparacion.py           Serie sin residentes y particiones temporales
    04_ajuste.py                Ajuste SARIMA y persistencia del modelo
    utils.py                    Lectura, escritura y validaciones compartidas
    run_pipeline.py             Ejecucion de las etapas disponibles
  data/
    raw/lab1/                   entrenamiento.csv y prueba.csv
    processed/                  Resultados regenerables, fuera de Git
  notebooks/                    Exploracion, fuera del flujo de ejecucion
  README.md                     Detalle del pipeline
```

## Requisitos

- Python 3.13 para el pipeline. Utilizamos la misma version menor en el equipo.
- Node.js 22.12 o posterior y pnpm 10.33.0 para el tablero.
- Git para clonar el repositorio privado.

La instalacion inicial necesita Internet para descargar dependencias. Los CSV
ya estan incluidos. No es necesario tener las carpetas de los laboratorios
anteriores. No se deben editar los archivos de `data/raw/`.

## Preparar el pipeline

Ejecutar los comandos desde la raiz del repositorio.

### macOS y Linux

```bash
python3.13 pipeline/src/00_init.py
source pipeline/.venv/bin/activate
python pipeline/src/config.py
```

### Windows con PowerShell

```powershell
py -3.13 pipeline/src/00_init.py
.\pipeline\.venv\Scripts\Activate.ps1
python pipeline/src/config.py
```

Si la terminal no permite activar el entorno, se puede usar directamente su Python:

```powershell
.\pipeline\.venv\Scripts\python.exe pipeline/src/config.py
```

`00_init.py` crea `pipeline/.venv/`, instala `requirements.txt` y comprueba que las
dependencias no tengan conflictos. Si se ejecuta otra vez, reutiliza el entorno
y comprueba la instalacion. No prepara datos ni entrena modelos.

`config.py` muestra la configuracion y calcula las rutas desde la ubicacion del
proyecto. No depende del nombre del usuario ni de la carpeta donde se clono.
Este comando todavia no ejecuta el pipeline completo.

Con el entorno activado, las etapas implementadas se ejecutan con un comando:

```bash
python pipeline/src/run_pipeline.py
```

Actualmente ejecuta ingesta, validacion, preparacion, ajuste SARIMA, evaluacion
exportacion candidata y decision de publicacion.
La ingesta genera `pipeline/data/processed/01_ingesta.csv`
y `01_ingesta.json`, que registra los archivos leidos, sus huellas SHA-256 y los
conteos de filas. Los valores originales se conservan como texto. La columna
`archivo_origen` identifica el CSV de procedencia y no define la nueva particion
de ajuste y evaluacion, que se construira con las fechas configuradas.

La ingesta se puede ejecutar por separado mediante
`python pipeline/src/01_ingesta.py`. Si falta un archivo, una columna necesaria
o los encabezados se repiten, se detiene antes de reemplazar su salida.

La validacion genera `pipeline/data/processed/02_validacion.json`. Si no hay
errores criticos, tambien genera `02_validado.csv` conservando todos los valores
y filas de la ingesta. Las advertencias quedan en el reporte y permiten continuar.
Ante un error critico, el comando se detiene y no reemplaza el CSV validado previo.

Las reglas de advertencia y detencion de cada control estan en
[pipeline/CONTROLES_CALIDAD.md](pipeline/CONTROLES_CALIDAD.md).

La preparacion exige que datos y configuracion coincidan con el reporte de calidad.
Excluye residentes, suma por mes y separa las fechas de ajuste y evaluacion.
Genera `03_serie_mensual.csv`, `03_ajuste.csv`, `03_evaluacion.csv` y el reporte
`03_preparacion.json`, dentro de `pipeline/data/processed/`. No completa meses
sin cobertura con cero ni utiliza la evaluacion para transformar el ajuste.
El diccionario de estas salidas esta en [pipeline/codebook.md](pipeline/codebook.md).

El ajuste utiliza unicamente los 36 meses de entrenamiento configurados. Guarda
`04_modelo_sarima.pkl` y `04_ajuste.json` en `pipeline/data/processed/`. El reporte
incluye parametros aprendidos, convergencia, advertencias, versiones y huellas.
Un ajuste sin convergencia se rechaza y conserva el modelo anterior. La etapa
siguiente calcula MAE y RMSE fuera de muestra. La etapa 7 decide la publicacion.

Las pruebas de las etapas implementadas se ejecutan con el entorno activado:

```bash
python -m unittest discover -s pipeline/tests -v
```

Utilizan archivos sinteticos temporales. Comprueban preservacion de valores,
repetibilidad, cobertura, duplicados, faltantes, tipos, valores y metodologia.
Los fallos no deben reemplazar salidas anteriores ni archivos de publicacion.

Las versiones de todas las dependencias estan fijadas en `requirements.txt`.
`requirements.in` identifica las cuatro que utilizaremos directamente:

| Paquete | Uso previsto |
|---|---|
| pandas | Leer CSV y construir la serie mensual |
| NumPy | Logaritmos, exponenciales y calculos de error |
| statsmodels | Ajustar SARIMA y generar predicciones |
| MLflow | Registrar datos, configuracion, controles, metricas y archivos |

El script instala dentro de `.venv/`, no en el Python global del sistema.
Con el entorno activado, `python -m pip check` permite comprobar las dependencias.
`deactivate` permite salir del entorno.

## Ejecutar el tablero

Desde la raiz del repositorio:

```bash
pnpm install --frozen-lockfile
pnpm run setup:hooks
pnpm dev
```

Abrir la direccion local que indique Next.js, normalmente
[localhost:3000](http://localhost:3000).
Los cambios de filtros solo afectan la visualizacion y no ejecutan modelos.

## Comprobaciones del frontend

```bash
pnpm run validate
pnpm build
```

`validate` ejecuta ESLint y la comprobacion de tipos. Los hooks utilizan
Conventional Commits y validan el frontend antes de cada commit.

## Documentacion

El detalle de configuracion y las etapas previstas estan en
[pipeline/README.md](pipeline/README.md).
Las reglas de calidad estan en [pipeline/CONTROLES_CALIDAD.md](pipeline/CONTROLES_CALIDAD.md).
El pipeline incluye la decision de publicacion. La integracion del tablero y los comandos Docker siguen pendientes.

## Evaluacion de SARIMA

La etapa `05_evaluacion.py` pronostica enero a junio de 2026 desde el cierre
del ajuste en diciembre de 2025. Compara las llegadas observadas con SARIMA
y con el mismo mes de 2025. Genera `05_comparacion.csv` y `05_evaluacion.json`
en `pipeline/data/processed/`.

La regla de `configuracion.toml` exige que MAE y RMSE de SARIMA sean menores
que los de la referencia. Un empate no supera la regla. Evaluar correctamente
no implica aprobar el modelo. Ningun resultado de esta etapa publica datos en
el tablero. El comando del pipeline ya incluye esta evaluacion.

## Exportacion candidata

La etapa `06_exportacion.py` prepara `06_candidato.json` y `06_exportacion.json`
en `pipeline/data/processed/`. Reune las seis estimaciones evaluadas, sus
metricas, la poblacion y las huellas de origen para revisarlas como un paquete.
El comando del pipeline ya incluye esta etapa.

El candidato conserva la decision de desempeno de la evaluacion. Si SARIMA no
supera la referencia, queda marcado como `no_supera_regla`. No se publica ni se
reemplazan los JSON del tablero. Tampoco se generan pronosticos para nuevos
meses. La etapa 7 decide si se puede activar una version. MLflow registra la
ejecucion y sus archivos. La integracion con el tablero sigue pendiente.

## Preparar MLflow local

Con el entorno Python activado, ejecutar desde la raiz:

```bash
python pipeline/src/seguimiento.py
```

Crea o recupera el experimento `laboratorio_11_turismo_guatemala` en SQLite.
La base `mlflow.db` y la carpeta `artefactos` quedan en
`pipeline/data/processed/mlflow/`, fuera de Git. Cada integrante conserva su
historial local. Este comando solo prepara la conexion. El orquestador registra
las metricas, el modelo y los archivos cuando ejecuta las etapas.

## Publicacion controlada

`07_publicacion.py` forma parte de `run_pipeline.py`. Comprueba la calidad,
la integridad del candidato y el resultado de desempeno antes de activar una
version. Un candidato que no supera la referencia termina como `no_publicado`.
Un insumo invalido detiene el flujo como error. En ambos casos se conserva la
version vigente, si existe.

Las versiones aprobadas se guardan en
`pipeline/data/processed/publicaciones/versiones/`. El archivo `vigente.json`
indica cual consultar y contiene su huella SHA-256. Si no existe ese archivo,
la consulta devuelve que no hay estimaciones aprobadas disponibles. El reporte
`pipeline/data/processed/07_publicacion.json` registra la decision.

Cada exportacion tiene un identificador local y una fecha UTC. Se conservan en
la version publicada junto con el destino, la unidad y las estimaciones. Este
identificador local se conserva junto con el run de MLflow que registra el
orquestador. La adaptacion del tablero heredado sigue pendiente. El tablero aun
consulta los JSON del laboratorio 10 y no utiliza este indicador.

## Ejercicio 4 de MLflow

Cada invocacion de `python pipeline/src/run_pipeline.py` crea un run que conserva
commit de Git, huellas de los scripts y fuentes, configuracion, periodos,
parametros, seis controles, metricas, estimaciones y modelo guardado. Se copian
los scripts realmente ejecutados para identificar tambien los cambios locales
que todavia no pertenecen al commit. Los archivos y registros son locales.

Una corrida completada queda en `FINISHED`, aunque el candidato no sea aprobado
para publicacion. Un error queda en `FAILED` con la etapa, la causa y su salida.
Si el flujo no llega a evaluar, el run no recibe metricas predictivas.

Para repetir la demostracion completa con los datos actuales:

```bash
python pipeline/src/evidencia_mlflow.py --verificar
```

Ejecuta dos corridas completas con los mismos datos y configuracion, compara
los archivos y metricas guardados en MLflow y provoca un fallo en una copia
temporal. El reporte queda en `pipeline/data/processed/evidencia_mlflow.json` y
en los archivos de evidencia de los tres runs. Los CSV originales no cambian.

Para consultar los registros sin volver a ejecutar modelos:

```bash
python pipeline/src/evidencia_mlflow.py
python pipeline/src/seguimiento.py --interfaz
```

La interfaz queda en [127.0.0.1:5000](http://127.0.0.1:5000).
Se detiene con Ctrl+C. El detalle de los requisitos, los archivos registrados,
las tolerancias y la entrega esta en [pipeline/EJERCICIO_4.md](pipeline/EJERCICIO_4.md).

## Ejercicio 5 de evaluacion y aceptacion

La evaluacion reserva enero a junio de 2026 y utiliza solo enero de 2023 a
diciembre de 2025 para ajustar SARIMA. El reporte identifica los meses ocultos,
el corte temporal y las limitaciones para reconstruir la informacion que
estaba publicada en enero y febrero de 2026.

`evaluacion.observaciones_comparables` declara la comparabilidad interna de los
valores de la base academica. Si es `false`, la evaluacion se detiene sin
calcular ni registrar errores predictivos. No se trata de una certificacion de
cifras oficiales. Las fuentes originales no se modifican.

La publicacion exige calidad, integridad, observaciones comparables y mejora
estricta de MAE y RMSE frente al mismo mes del anio anterior. SARIMA no supera
la referencia y sigue sin publicarse. La justificacion de los umbrales, los
resultados y las limitaciones estan en [pipeline/EJERCICIO_5.md](pipeline/EJERCICIO_5.md).
