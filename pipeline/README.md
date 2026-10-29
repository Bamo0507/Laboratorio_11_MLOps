# Pipeline de llegadas mensuales a Guatemala

El pipeline se construye por etapas. Actualmente estan disponibles los dos CSV
de entrada, la configuracion, el setup de Python, la ingesta, los seis controles
de calidad, la preparacion de la serie, el ajuste SARIMA y la evaluacion
predictiva, la exportacion candidata y la decision de publicacion. El registro
de ejecuciones en MLflow y la integracion con el tablero siguen pendientes.

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
El registro de ejecuciones en MLflow y la integracion del tablero siguen
pendientes. La etapa 7 implementa la decision de publicacion.

La generacion del horizonte utiliza
[get_forecast de statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.get_forecast.html).

## Etapa 6 de exportacion candidata

```text
05_comparacion.csv + 05_evaluacion.json + certificados anteriores
  -> 06_exportacion.py
  -> 06_candidato.json + 06_exportacion.json
```

| Etapa | Archivo | Responsabilidad | Entrada | Salida |
| --- | --- | --- | --- | --- |
| 6 | 06_exportacion.py | Empaquetar las estimaciones evaluadas para revision | Comparacion, evaluacion y certificados vigentes | Candidato JSON y reporte de exportacion |

```bash
python pipeline/src/06_exportacion.py
```

El orquestador incluye esta etapa. El candidato contiene las seis estimaciones
ya evaluadas, las llegadas observadas, la referencia, los errores, las metricas,
los periodos y la configuracion del modelo. No entrena otro modelo ni extiende
el horizonte despues de junio de 2026. Sus fechas corresponden a evaluacion de
observaciones conocidas, no a una nueva proyeccion futura.

Se verifica que no hayan cambiado la comparacion, la evaluacion, el modelo,
los reportes previos, los datos preparados, los CSV originales y la configuracion.
Se vuelven a calcular las metricas desde el CSV para comprobar su coherencia
con el reporte. La tolerancia numerica solo admite diferencias de serializacion.
La regla de desempeno sigue utilizando desigualdades estrictas.

Un desempeno desfavorable genera un candidato para auditoria marcado como
`no_supera_regla`. No se sustituye SARIMA por la referencia ni se cambia el
criterio de aceptacion. Un desempeno favorable queda marcado como `supera_regla`,
pero tampoco autoriza publicar en esta etapa. Un insumo invalido rechaza la
exportacion y conserva el candidato anterior. Los consumidores deben exigir
un reporte completado y la huella del candidato coincidente.

El candidato tiene un contrato propio y todavia no es un reemplazo directo de
los JSON del tablero heredado. No agrega modelos, series, MAPE ni intervalos que
no hayan sido calculados. Todo se guarda en `data/processed/`. El registro en
La etapa 7 implementa la decision de publicacion. El registro en MLflow y la
integracion con el tablero siguen pendientes.

## Seguimiento local con SQLite

Se eligio SQLite para guardar el historial de MLflow en esta computadora.
`configuracion.toml` declara `seguimiento.almacen = "sqlite"` y el experimento
`laboratorio_11_turismo_guatemala`. Un experimento agrupa ejecuciones del mismo
trabajo. Cada ejecucion tendra su propio identificador dentro de ese grupo.

La carpeta configurada en `rutas.mlflow` es `data/processed/mlflow`. Alli se
guarda `mlflow.db` para parametros, metricas y estados, y una carpeta
`artefactos` para modelos y reportes. Estas rutas se resuelven desde la carpeta
del pipeline, sin depender de la computadora ni del directorio de ejecucion.

El auxiliar `src/seguimiento.py` conecta MLflow con SQLite y crea el experimento
si no existe. Al repetirlo recupera el mismo experimento. MLflow ya esta incluido
en las dependencias del entorno. Con el entorno activado se ejecuta desde la
raiz del repositorio:

```bash
python pipeline/src/seguimiento.py
```

El comando muestra el nombre y el identificador del experimento. Crea la base
y la carpeta de artefactos, pero no crea ejecuciones, no registra metricas y no
vuelve a entrenar el modelo. Todavia no forma parte de `run_pipeline.py`, porque
estamos comprobando la conexion antes de incorporar el registro completo.

El cliente recibe explicitamente la direccion de la base local. Las variables
`MLFLOW_TRACKING_URI` y `MLFLOW_REGISTRY_URI` del entorno no cambian ese destino.
Un experimento eliminado se rechaza sin restaurarlo automaticamente.
Si una base copiada declara otra ubicacion de artefactos, se detiene para evitar
escribir archivos en una carpeta distinta. Para otra computadora, se prepara su
propio historial desde el repositorio, sin copiar `data/processed/`.

La creacion y recuperacion utilizan el
[cliente de MLflow](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.client.html#mlflow.client.MlflowClient.create_experiment).

El historial y los artefactos generados quedan fuera de Git. Cada integrante
tendra su propio historial local. Compartir el repositorio no sincroniza estas
bases. SQLite no requiere instalar un servidor de base de datos separado.

## Etapa 7 de publicacion controlada

```text
06_candidato.json + 06_exportacion.json + certificados anteriores
  -> 07_publicacion.py
  -> 07_publicacion.json
  -> si se aprueba, publicaciones/versiones/<version>.json
  -> activacion atomica de publicaciones/vigente.json
```

| Etapa | Archivo | Responsabilidad | Entrada | Salida |
| --- | --- | --- | --- | --- |
| 7 | 07_publicacion.py | Activar solo una version aprobada | Candidato, exportacion y certificados vigentes | Reporte de decision y version aprobada si corresponde |

```bash
python pipeline/src/07_publicacion.py
```

El orquestador ya incluye esta etapa. Al modificar la configuracion se deben
regenerar las etapas anteriores, porque las huellas certifican su contenido.

La publicacion exige que sigan vigentes los datos originales, los reportes,
la configuracion y los resultados intermedios. Se recalculan los controles de
coherencia de la etapa 6 y se compara todo el contenido del candidato con los
resultados certificados. El archivo candidato conserva su estado pendiente.
La autorizacion solo aparece en la version aprobada.

Si SARIMA no supera MAE y RMSE de la referencia, la decision es `no_publicado`.
Esto completa correctamente el paso de decision, sin activar estimaciones. Un
archivo alterado, un bloqueo de otro escritor o un error de escritura rechaza
la ejecucion. Ninguno de estos casos reemplaza una version vigente valida.

Las versiones aprobadas contienen las estimaciones, destino, unidad, periodo,
metricas y configuracion, junto con la fecha de generacion y el identificador
local de la exportacion. Todavia no hay un run de MLflow asociado. Ese enlace
se agregara al implementar el registro de ejecuciones. El identificador y la
fecha son metadatos nuevos por exportacion, no componentes aleatorios del
modelo. La equivalencia de resultados se comprueba sobre las estimaciones y
metricas, no sobre la igualdad de estos identificadores.

La version se identifica mediante la huella combinada del candidato y el
reporte de exportacion. Cada version se guarda sin sobrescribir versiones
anteriores. Repetir la publicacion del mismo candidato certificado conserva
la misma version. Una nueva exportacion tiene otro identificador y puede
generar una nueva version aun con estimaciones equivalentes.

`publicacion.consultar_vigente` solo consulta el indicador aprobado y verifica
la huella de la version. No consulta candidatos como alternativa. Si el indicador
no existe devuelve `None`, que representa estimaciones no disponibles. Si existe
pero su contenido o su version estan corruptos, se genera un error.

Se guarda primero la version, luego el reporte y finalmente se activa el
indicador con un temporal y reemplazo atomico. El indicador es la fuente de
verdad para saber que version esta activa. Si el proceso se interrumpe antes
de activarlo, puede quedar una version guardada sin activar o un reporte que
describa una activacion aun no realizada. Reejecutar el mismo paso permite
completarla sin sobrescribir el contenido de la version.

Un archivo `.publicacion.lock` evita dos escritores simultaneos. Si un proceso
se termina abruptamente puede dejar ese bloqueo. Solo se debe retirarlo despues
de comprobar que no queda un proceso de publicacion en ejecucion. El comando
no elimina bloqueos de otros escritores.

Estas versiones siguen en `data/processed/` y fuera de Git. La conexion del
indicador con el tablero es un paso posterior. El tablero heredado todavia usa
los JSON del laboratorio 10. Tampoco se ha implementado aun un comando de
restauracion, aunque las versiones anteriores se conservan para ese paso.
