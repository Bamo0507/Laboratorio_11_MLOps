# Entorno del pipeline y de la interfaz de MLflow.
# Los CSV, los resultados y el historial se montan al ejecutar; no forman parte de la imagen.
FROM python:3.13.14-slim

# git solo identifica el commit del repositorio montado en /app/.git.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GIT_CONFIG_COUNT=1 \
    GIT_CONFIG_KEY_0=safe.directory \
    GIT_CONFIG_VALUE_0=/app

WORKDIR /app
COPY requirements.txt pipeline/requirements.txt
RUN pip install --no-cache-dir -r pipeline/requirements.txt
COPY . pipeline/

CMD ["python", "pipeline/src/run_pipeline.py"]
