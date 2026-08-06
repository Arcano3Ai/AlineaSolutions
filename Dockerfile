# --- ETAPA 1: Compilación y Preparación de Dependencias ---
FROM python:3.10-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema requeridas para compilar algunos paquetes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instalar dependencias en una carpeta local para copiar en la etapa de ejecución
RUN pip install --no-cache-dir --user -r requirements.txt


# --- ETAPA 2: Entorno de Ejecución Ligero ---
FROM python:3.10-slim AS runner

WORKDIR /app

# Copiar dependencias compiladas desde la etapa anterior
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Pre-descargar el modelo de embeddings para evitar descargas lentas y bloqueos en runtime en Cloud Run
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copiar los recursos del proyecto
COPY app.py .
COPY database/ database/
COPY classifiers/ classifiers/
COPY sources/ sources/
COPY utils/ utils/
COPY static/ static/
COPY templates/ templates/
COPY data/ data/
COPY instance/ instance/
# COPY conocimiento/ conocimiento/

# Configurar variables de entorno predeterminadas
ENV PORT=8080
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Exponer el puerto de Google Cloud Run
EXPOSE 8080

# Arrancar con gunicorn (WSGI de producción):
#   - 2 workers para Cloud Run (1 CPU asignada por defecto)
#   - timeout 120s para requests de clasificación con IA
#   - bind en 0.0.0.0:PORT para Cloud Run
CMD exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app
