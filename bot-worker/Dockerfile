# bot-worker/Dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Копируем shared модули
COPY ../shared /app/shared

# Копируем код bot-worker
COPY . .

# Добавляем shared в PYTHONPATH
ENV PYTHONPATH="/app:${PYTHONPATH}"

RUN useradd -m -u 1000 botworker && chown -R botworker:botworker /app
USER botworker

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "main.py"]