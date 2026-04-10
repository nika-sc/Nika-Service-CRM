#!/bin/bash
set -e

# Применяем миграции при старте
echo "Running migrations..."
python scripts/run_migrations.py || true

# Запускаем Gunicorn
# Для VPS держим консервативный default по воркерам, чтобы избежать OOM.
WEB_CONCURRENCY="${WEB_CONCURRENCY:-1}"
WEB_THREADS="${WEB_THREADS:-8}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --worker-class gthread \
  --workers "${WEB_CONCURRENCY}" \
  --threads "${WEB_THREADS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --limit-request-line 8192 \
  wsgi:app
