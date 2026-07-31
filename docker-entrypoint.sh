#!/bin/bash
set -e

# Применяем миграции при старте
echo "Running migrations..."
python scripts/run_migrations.py || true

# Запускаем Gunicorn
# Default: несколько воркеров для параллельных пользователей.
# На маленьком VPS (~1 ГБ / 1 CPU) лучше WEB_CONCURRENCY=2 WEB_THREADS=4.
WEB_CONCURRENCY="${WEB_CONCURRENCY:-3}"
WEB_THREADS="${WEB_THREADS:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
exec gunicorn \
  --bind 0.0.0.0:5000 \
  --worker-class gthread \
  --workers "${WEB_CONCURRENCY}" \
  --threads "${WEB_THREADS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --limit-request-line 8192 \
  wsgi:app
