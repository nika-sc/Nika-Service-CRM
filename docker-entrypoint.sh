#!/bin/bash
set -e

# Каталоги загрузок на томе (диагностика, комментарии, чат, счета)
mkdir -p /app/uploads/order_client /app/uploads/comments \
  /app/data/uploads/staff_chat /app/static/uploads/invoices

# Применяем миграции при старте
echo "Running migrations..."
python scripts/run_migrations.py || true

# Запускаем Gunicorn
# Default: несколько воркеров для параллельных пользователей.
# На маленьком VPS (~1 ГБ / 1 CPU) лучше WEB_CONCURRENCY=2 WEB_THREADS=4.
# WORK (2+ CPU): WEB_CONCURRENCY=4 WEB_THREADS=6.
WEB_CONCURRENCY="${WEB_CONCURRENCY:-3}"
WEB_THREADS="${WEB_THREADS:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
GUNICORN_MAX_REQUESTS="${GUNICORN_MAX_REQUESTS:-1500}"
GUNICORN_MAX_REQUESTS_JITTER="${GUNICORN_MAX_REQUESTS_JITTER:-150}"
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --worker-class gthread \
  --workers "${WEB_CONCURRENCY}" \
  --threads "${WEB_THREADS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --max-requests "${GUNICORN_MAX_REQUESTS}" \
  --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER}" \
  --limit-request-line 8192 \
  wsgi:app
