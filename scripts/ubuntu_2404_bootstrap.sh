#!/usr/bin/env bash
# Автоматическая подготовка Ubuntu 24.04 LTS: зависимости, venv, PostgreSQL, демо-дамп.
# Репозиторий уже должен лежать в $DEST (например после git clone или git clone из .bundle).
set -euo pipefail

DEST="${DEST:-/root/Nika-Service-CRM}"

if [[ ! -f "$DEST/requirements.txt" ]]; then
  echo "Ошибка: не найден $DEST/requirements.txt (задайте DEST=... или клонируйте репозиторий)."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  git python3 python3-venv python3-pip \
  build-essential pkg-config libcairo2-dev libpq-dev \
  postgresql postgresql-client curl

if [[ ! -d "$DEST/venv" ]]; then
  python3 -m venv "$DEST/venv"
fi
"$DEST/venv/bin/pip" install -q --upgrade pip
"$DEST/venv/bin/pip" install -q -r "$DEST/requirements.txt"

NIKA_PASS="$(openssl rand -hex 16)"
SECRET="$(openssl rand -hex 32)"

sudo -u postgres psql -c "CREATE USER nikacrm WITH PASSWORD '${NIKA_PASS}'" 2>/dev/null \
  || sudo -u postgres psql -c "ALTER USER nikacrm WITH PASSWORD '${NIKA_PASS}'"

if ! sudo -u postgres psql -Atc "SELECT 1 FROM pg_database WHERE datname='nikacrm'" | grep -q 1; then
  sudo -u postgres psql -c "CREATE DATABASE nikacrm OWNER nikacrm;"
fi

HAS_USERS="$(sudo -u postgres psql -d nikacrm -Atc \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='users';" || echo 0)"

if [[ "${HAS_USERS}" != "1" ]]; then
  if [[ ! -f "$DEST/database/bootstrap/nikacrm_public_sanitized.sql" ]]; then
    echo "Ошибка: нет файла database/bootstrap/nikacrm_public_sanitized.sql"
    exit 1
  fi
  # psql от пользователя postgres не читает файлы из /root (политика доступа) — копируем во /tmp
  cp "$DEST/database/bootstrap/nikacrm_public_sanitized.sql" /tmp/nikacrm_public_sanitized.sql
  chmod 644 /tmp/nikacrm_public_sanitized.sql
  sudo -u postgres psql -d nikacrm -v ON_ERROR_STOP=1 -f /tmp/nikacrm_public_sanitized.sql
  rm -f /tmp/nikacrm_public_sanitized.sql
fi

# В OSS-репозитории каталог save/ не входит в git — выдаём права явно (аналог save/scripts/grant_app_user_after_vps_restore.sql)
sudo -u postgres psql -d nikacrm -v ON_ERROR_STOP=1 <<'EOSQL'
GRANT USAGE ON SCHEMA public TO nikacrm;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nikacrm;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nikacrm;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nikacrm;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO nikacrm;
EOSQL

if [[ -f "$DEST/save/scripts/grant_app_user_after_vps_restore.sql" ]]; then
  cp "$DEST/save/scripts/grant_app_user_after_vps_restore.sql" /tmp/grant_app_user_after_vps_restore.sql
  chmod 644 /tmp/grant_app_user_after_vps_restore.sql
  sudo -u postgres psql -d nikacrm -v ON_ERROR_STOP=1 -f /tmp/grant_app_user_after_vps_restore.sql
  rm -f /tmp/grant_app_user_after_vps_restore.sql
fi

umask 077
cat >"$DEST/.env" <<EOF
SECRET_KEY=${SECRET}
FLASK_ENV=production
FLASK_DEBUG=False
DB_DRIVER=postgres
DATABASE_URL=postgresql://nikacrm:${NIKA_PASS}@127.0.0.1:5432/nikacrm
RATELIMIT_STORAGE_URI=memory://
TIMEZONE_OFFSET=3
EOF
chmod 600 "$DEST/.env"

cd "$DEST"
./venv/bin/python scripts/run_migrations.py

echo "Готово. Пароль БД сохранён только в $DEST/.env (пользователь nikacrm)."
echo "Проверка: cd $DEST && ./venv/bin/python -c \"from app import create_app; from app.config import config; create_app(config['production'])\""
