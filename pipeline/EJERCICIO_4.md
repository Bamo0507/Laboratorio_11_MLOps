# Registro de ejecuciones con MLflow

El experimento `laboratorio_11_turismo_guatemala` agrupa las ejecuciones del
pipeline nacional sin residentes. Se usa SQLite local en
`data/processed/mlflow/mlflow.db` y los archivos quedan en `artefactos` dentro
de esa misma carpeta. Las rutas se calculan desde la configuracion.

## 4.1 Informacion conservada por ejecucion

| Requisito | Registro en MLflow |
| --- | --- |
| Identificador y fecha | Run ID y horas de inicio y finalizacion en UTC |
| Version del codigo | Etiqueta mlflow.source.git.commit, indicador de cambios locales, copia de los scripts y sus huellas en codigo/version.json |
| Fuentes y periodos | Rutas relativas, tamano y SHA-256 en datos/fuentes.json, parametros de fuentes y fechas de ajuste y evaluacion |
| Parametros | Configuracion del SARIMA, poblacion, referencia, reglas y tolerancias. Parametros aprendidos despues del ajuste |
| Metricas | sarima.mae, sarima.rmse, referencia.mae y referencia.rmse, despues de completar la evaluacion |
| Calidad | Estado de cada uno de los seis controles y reporte 02_validacion.json |
| Estimaciones y configuracion | Serie mensual, particiones, comparacion, candidato, reporte de exportacion y copia de la configuracion |
| Modelo | 04_modelo_sarima.pkl y reporte con los parametros aprendidos y versiones del entorno |
| Fallos | Estado FAILED o KILLED, etapa, causa completa en ejecucion/error.json y salida de consola por etapa |

El codigo que aun tiene cambios locales no se presenta como si coincidiera
exactamente con el commit. MLflow conserva ese estado y copia los scripts que
se ejecutaron, ademas de sus huellas. No se hace commit automaticamente.

Los CSV crudos y los archivos intermedios con microdatos no se copian al
historial. Se registran su identificacion y huellas. Los datos originales ya
estan en el repositorio privado. Los archivos agregados, reportes y modelo se
conservan por run y no se sustituyen al iniciar otra corrida.

El orquestador vincula `06_exportacion.json` con el run mediante
`id_ejecucion_mlflow`. Una version aprobada y sus registros mensuales conservan
ese identificador. El identificador local de exportacion se mantiene como
referencia adicional. Ejecutar una exportacion individual sin el orquestador
no crea ni inventa un run.

## 4.2 Dos ejecuciones equivalentes

Con el entorno activado, desde la raiz del repositorio:

```bash
python pipeline/src/evidencia_mlflow.py --verificar
```

Este comando ejecuta el pipeline dos veces con los mismos datos y configuracion.
Despues descarga los archivos de cada run mediante el cliente de MLflow y
compara los parametros configurados, las fuentes, el commit, las huellas de los
scripts, la serie mensual, los conjuntos de ajuste y evaluacion, la comparacion
mensual, los parametros del modelo guardado, las cuatro metricas y los seis
controles. No se limita a leer los ultimos archivos de `data/processed`.

Las tolerancias se configuran en `seguimiento` dentro de `configuracion.toml`.
Se admite una diferencia absoluta de 1e-8 mas una diferencia relativa de 1e-12
respecto del valor comparado. La tolerancia solo afecta la comprobacion de
reproducibilidad. No flexibiliza la regla de desempeno, que sigue exigiendo
MAE y RMSE estrictamente menores que la referencia.

El ajuste es determinista en el entorno fijado. Entre plataformas puede haber
pequenas diferencias de coma flotante por las bibliotecas numericas. El reporte
indica la diferencia maxima observada, por lo que no se atribuyen diferencias
a esta causa sin comprobarlas. Los identificadores y las fechas cambian entre
runs y se conservan como metadatos, sin exigir que sean iguales.

## 4.3 Fallos y evidencia de consulta

El mismo comando prepara una copia temporal de la configuracion y los dos CSV.
Retira la columna de llegadas de la copia y ejecuta la ingesta. El run debe
terminar como FAILED, identificar la columna ausente y no tener metricas
predictivas. La copia utiliza el experimento del proyecto para que el fallo y
las dos corridas completas puedan consultarse juntos. Sus salidas se escriben
en la carpeta temporal. Los datos y las publicaciones reales no se modifican.

El reporte `data/processed/evidencia_mlflow.json` conserva los identificadores,
la comparacion y la consulta de los tres runs. Cada consulta incluye parametros,
metricas, etiquetas, estados y el listado de archivos realmente disponibles.
La evidencia tambien se incorpora a esos runs. Es un complemento verificable
de los registros persistidos, no un sustituto de ellos.

Para consultar el historial sin ejecutar modelos:

```bash
python pipeline/src/evidencia_mlflow.py
```

Para consultar la interfaz:

```bash
python pipeline/src/seguimiento.py --interfaz
```

Abrir `http://127.0.0.1:5000`, entrar al experimento y seleccionar las corridas.
La opcion `--puerto` permite elegir otro puerto. El servidor se limita a esta
computadora y se detiene con Ctrl+C. No se necesita una cuenta ni credenciales.

Una corrida que completa el flujo queda como FINISHED aunque el candidato
termine como no_publicado. FAILED representa un error que impidio completar el
flujo. Una interrupcion del proceso principal por teclado se registra como
KILLED. Un cierre abrupto o la perdida de acceso a SQLite pueden impedir el
registro de la finalizacion y requieren revision.

Para entregar los registros deben conservarse la base SQLite y la carpeta de
artefactos completas por un medio autorizado, junto con el reporte de evidencia.
No basta con capturas ni con el JSON de consulta. Estos archivos estan fuera de
Git porque son generados. Las ubicaciones locales de artefactos se guardan en
SQLite. Copiar solo la base a otra computadora no traslada el modelo ni los
reportes. La configuracion de persistencia y ubicaciones de Docker se abordara
en el ejercicio de contenerizacion.

Los comandos, las pruebas y los scripts de verificacion si se versionan.

## Verificacion realizada

Se conservaron las siguientes ejecuciones consultables en el experimento local.

| Run | Estado | Resultado |
| --- | --- | --- |
| 1ff5c913ebee434ab76a1aa0ef11bd47 | FINISHED | Siete etapas completadas y cuatro metricas |
| dc04c5cd54ec405c88bd36b8e7fe3b8f | FINISHED | Siete etapas completadas y cuatro metricas |
| 837406a9987b4b0c8f3fc8b2401e285f | FAILED | Columna de llegadas ausente en una copia temporal, sin metricas predictivas |

La diferencia numerica maxima fue cero en las cuatro metricas y en los valores
de las series y comparaciones guardadas. Los parametros de los modelos
recuperados tambien resultaron equivalentes. Las dos corridas conservaron las
mismas fuentes, configuracion, commit y huellas de los scripts. SARIMA mantuvo
la decision `no_publicado` en ambas, sin cambiar el criterio de desempeno.

Algunas huellas de reportes y archivos PKL difieren. La equivalencia exigida no
es igualdad binaria de todo el historial. Los reportes incorporan huellas de
otros archivos, identificadores y fechas. Para el modelo serializado se
compararon los parametros recuperados y los valores pronosticados. No se
observaron diferencias numericas en los resultados comparados.

Las capturas `data/processed/mlflow_comparacion.jpg` y
`data/processed/mlflow_fallo.jpg` muestran la consulta en la interfaz. Tambien
se incorporaron como archivos de evidencia en los tres runs. El JSON de consulta
conserva los datos completos que las capturas no muestran. La comprobacion de
las fuentes originales y del indicador vigente confirmo que la prueba de fallo
no los modifico. Pasaron 64 pruebas automatizadas.
