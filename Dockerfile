# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
WORKDIR /app

RUN useradd --system --home /var/lib/homenetiq --create-home homenetiq \
    && mkdir -p /data \
    && chown homenetiq:homenetiq /data

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY dashboard /app/dashboard
COPY collectors /app/collectors
COPY agents /app/agents
COPY probes /app/probes

ENV HOMENETIQ_DB_PATH=/data/homenetiq.sqlite3 \
    PYTHONUNBUFFERED=1

USER homenetiq
EXPOSE 8080 8501
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
