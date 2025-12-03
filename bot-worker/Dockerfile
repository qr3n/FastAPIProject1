FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY bot-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем shared модули в корень /app
COPY shared/ ./shared/

# Копируем код bot-worker в корень /app (без создания подпапки)
COPY bot-worker/*.py ./
COPY bot-worker/handlers/ ./handlers/

# PYTHONPATH уже содержит /app, где лежат shared и все модули bot-worker
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Создаем пользователя
RUN useradd -m -u 1000 botworker && chown -R botworker:botworker /app
USER botworker

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "main.py"]