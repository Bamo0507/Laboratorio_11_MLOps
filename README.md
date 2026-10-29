# Laboratorio 11 de MLOps

Este proyecto continua el tablero del laboratorio 10 sobre llegadas de turistas
y excursionistas a Guatemala. El laboratorio 11 incorpora un pipeline de Python
para preparar datos, ejecutar SARIMA, evaluar sus predicciones y publicar
resultados aprobados con trazabilidad en MLflow.

## Estado actual

El tablero heredado esta en `src/`. En `pipeline/` ya estan los CSV originales,
la configuracion portable, la preparacion del entorno, la ingesta y los seis
controles de calidad. El modelado y la publicacion se implementaran despues.
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

Actualmente ejecuta ingesta y validacion. La ingesta genera `pipeline/data/processed/01_ingesta.csv`
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

Las pruebas de ingesta y calidad se ejecutan con el entorno activado:

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
Los comandos de ejecucion completa, publicacion, MLflow y Docker se agregaran
cuando esas partes esten implementadas y verificadas.
