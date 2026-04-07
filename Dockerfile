# NikaNewCrm - Production Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Системные зависимости (reportlab, barcode, pycairo/xhtml2pdf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libcairo2-dev \
    libpq-dev \
    postgresql-client \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python-зависимости (без dev-инструментов для меньшего образа)
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/
COPY oh-oh-icq-sound.mp3 .
COPY wsgi.py .
COPY run.py .
COPY scripts/run_migrations.py ./scripts/

# Создаём директории для БД и логов
RUN mkdir -p /app/database /app/logs

# Порт приложения
EXPOSE 5000

# Переменные окружения по умолчанию (переопределяются через .env)
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Entrypoint: миграции, затем gunicorn
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
