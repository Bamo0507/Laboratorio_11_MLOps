# Docker y verificacion desde una copia limpia

Los comandos de uso estan en la seccion Ejecutar con Docker del README de la
raiz. Aqui se resumen las decisiones y la comprobacion realizada.

## Servicios

| Servicio | Imagen | Inicio | Funcion |
| --- | --- | --- | --- |
| tablero | Dockerfile de la raiz, Node.js 22 | `docker compose up -d` | Next.js en modo produccion. Lee las publicaciones montadas en solo lectura |
| mlflow | pipeline/Dockerfile, Python 3.13 | `docker compose up -d` | Prepara el experimento y abre la interfaz sobre la base SQLite |
| pipeline | pipeline/Dockerfile | `docker compose run --rm pipeline` | Ejecuta las ocho etapas y termina |

El pipeline tiene un perfil propio para no ejecutarse con `up`. Espera el
healthcheck de MLflow porque dos procesos que crean la misma base SQLite al
mismo tiempo provocaron un error de migracion en la primera prueba.

## Datos, persistencia y trazabilidad

- Los CSV se montan desde `pipeline/data/raw` o desde `DATOS_INSTITUCIONALES`,
  en solo lectura. Ambos `.dockerignore` excluyen las carpetas de datos.
- Resultados, registros, MLflow y versiones se montan desde
  `pipeline/data/docker`, o `RESULTADOS`. Sobreviven a `docker compose down`.
- La carpeta es distinta de `pipeline/data/processed` porque MLflow guarda la
  ruta absoluta de los artefactos. Dentro del contenedor siempre es `/app/...`.
- `.git` se monta en solo lectura para registrar el commit y si el codigo de la
  imagen difiere de ese commit. `PYTHONDONTWRITEBYTECODE` evita archivos
  temporales que aparecerian como cambios locales.
- Las imagenes base fijan Python 3.13.14 y Node.js 22.21.1. Las dependencias
  vienen de `requirements.txt` y `pnpm-lock.yaml`.
- Los puertos se publican solo en `127.0.0.1` y se pueden cambiar con
  `PUERTO_TABLERO` y `PUERTO_MLFLOW`.

## Comprobacion realizada

Se copiaron solo los archivos versionados del repositorio a una carpeta nueva,
sin `node_modules`, `.venv` ni `data/processed`, y se inicio un repositorio Git
en ella. Desde esa copia:

1. `docker compose build` construyo las dos imagenes.
2. `docker compose up -d` dejo MLflow `healthy` y el tablero respondio 200.
   Pronosticos mostro Estimaciones no disponibles.
3. `docker compose run --rm pipeline` termino `FINISHED` con decision
   `no_publicado`. El run registro el commit de la copia y
   `codigo.cambios_locales = false`.
4. La API de MLflow devolvio los artefactos del run, incluido
   `ejecucion/registro.json`, servidos desde la carpeta montada.
5. `evidencia_recuperacion.py` completo los cinco pasos dentro del contenedor.
   Con `TURISMO_PUBLICACIONES_DIR` apuntando a la prueba, el tablero mostro la
   version A restaurada con la advertencia de datos sinteticos.
6. `restaurar.py --version` reactivo la version C y el tablero la mostro al
   consultar la actualizacion, sin reiniciar el contenedor.
7. Despues de `docker compose down` no quedaron contenedores. Con
   `docker compose up -d` MLflow conservo los 7 runs, 2 de ellos fallidos, y el
   tablero siguio mostrando la version C.

La copia de prueba uso los puertos 3100 y 5100 porque 3000 estaba ocupado por
otro proyecto y 5000 por AirPlay de macOS. Las pruebas se hicieron en macOS con
Docker Desktop sobre arm64. No se probo en Windows ni en Linux x86_64.
