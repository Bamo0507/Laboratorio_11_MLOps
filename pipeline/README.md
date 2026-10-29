# Pipeline de llegadas mensuales a Guatemala

El pipeline se construye por etapas. Actualmente estan disponibles los dos CSV
de entrada y la carga de configuracion. Todavia no se ejecutan la preparacion,
el ajuste, la evaluacion ni la publicacion.

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

Se requiere Python 3.11 o posterior para leer TOML con la biblioteca estandar.
Desde la raiz del repositorio:

```bash
python3 pipeline/src/config.py
```

En Windows se puede usar `py -3` en lugar de `python3`.
La salida muestra la configuracion y las rutas resueltas en esa computadora.
Ver una ruta completa en la salida es normal. Se calcula durante la ejecucion,
no esta escrita en los scripts ni en el TOML.

Esta comprobacion solo lee la configuracion. No entrena modelos ni comprueba
todavia los seis controles de calidad de los datos.

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

Los umbrales de aceptacion y las versiones de las dependencias del modelado se
definiran antes de ejecutar la evaluacion. Esta configuracion inicial no
autoriza publicaciones.
