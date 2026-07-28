#!/usr/bin/env bash
# Безопасное обновление существующей установки Nika CRM на Linux.
#
# Сохраняет: PostgreSQL-данные, .env, static/uploads, data/
# Перед изменениями: полный архив (pg_dump -Fc + tar.xz дерева + копия .env).
#
# Использование (из корня CRM):
#   sudo bash scripts/linux_upgrade.sh
#   REF=production sudo bash scripts/linux_upgrade.sh          # git ff-only
#   BUNDLE=/path/to/source.tar.gz sudo bash scripts/linux_upgrade.sh
#   SKIP_STOP=1 bash scripts/linux_upgrade.sh                 # не останавливать сервис
#
# Откат при сбое:
#   1) Архив лежит в data/database/backups/upgrade_YYYYmmdd_HHMMSS/
#   2) Восстановите .env из копии в каталоге архива
#   3) pg_restore dump (или docker volume) + распакуйте files.tar.xz поверх
#   4) Перезапустите сервис / compose
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

REF="${REF:-}"
BUNDLE="${BUNDLE:-}"
SKIP_STOP="${SKIP_STOP:-0}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:5000/}"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$ROOT_DIR/data/database/backups/upgrade_${TS}"
LOG() { echo "[linux_upgrade $(date '+%H:%M:%S')] $*"; }

die() { LOG "ERROR: $*"; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "нужна команда: $1"
}

detect_mode() {
  if [[ -f "$ROOT_DIR/docker-compose.yml" ]] || [[ -f "$ROOT_DIR/compose.yaml" ]]; then
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
      if docker compose ps >/dev/null 2>&1; then
        echo "docker"
        return
      fi
    fi
  fi
  if [[ -d "$ROOT_DIR/venv" ]] || [[ -d "$ROOT_DIR/.venv" ]]; then
    echo "venv"
    return
  fi
  echo "unknown"
}

load_dotenv_var() {
  local key="$1"
  if [[ -f "$ROOT_DIR/.env" ]]; then
    # shellcheck disable=SC1091
    set -a
    # shellcheck disable=SC1090
    source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ROOT_DIR/.env" | sed 's/\r$//' || true)
    set +a
  fi
  eval "echo \"\${$key:-}\""
}

MODE="$(detect_mode)"
LOG "Режим: $MODE  ROOT=$ROOT_DIR"
[[ -f "$ROOT_DIR/requirements.txt" ]] || die "не найден requirements.txt — запустите из корня CRM"
[[ -f "$ROOT_DIR/.env" ]] || die "нет .env — апгрейд без конфига опасен; создайте .env вручную"

mkdir -p "$BACKUP_DIR"
cp -a "$ROOT_DIR/.env" "$BACKUP_DIR/env.copy"
chmod 600 "$BACKUP_DIR/env.copy"

# --- полный бэкап ---
LOG "Архивация в $BACKUP_DIR"
if [[ "$MODE" == "docker" ]]; then
  require_cmd docker
  require_cmd tar
  PG_USER="$(docker compose exec -T postgres printenv POSTGRES_USER 2>/dev/null | tr -d '\r' || true)"
  PG_DB="$(docker compose exec -T postgres printenv POSTGRES_DB 2>/dev/null | tr -d '\r' || true)"
  PG_USER="${PG_USER:-postgres}"
  PG_DB="${PG_DB:-nikacrm}"
  docker compose exec -T postgres pg_dump -U "$PG_USER" -d "$PG_DB" -Fc > "$BACKUP_DIR/postgres.dump" \
    || die "pg_dump (docker) не удался"
else
  require_cmd tar
  DATABASE_URL="$(load_dotenv_var DATABASE_URL)"
  if [[ -n "${DATABASE_URL}" ]]; then
    if command -v pg_dump >/dev/null 2>&1; then
      pg_dump --format=custom --file="$BACKUP_DIR/postgres.dump" "$DATABASE_URL" \
        || die "pg_dump не удался"
    else
      LOG "WARN: pg_dump не найден — только файловый архив"
    fi
  else
    LOG "WARN: DATABASE_URL пуст — только файловый архив"
  fi
fi

tar -I 'xz -T0' -cf "$BACKUP_DIR/files.tar.xz" \
  -C "$ROOT_DIR" \
  --exclude='./.git' \
  --exclude='./.cursor' \
  --exclude='./data/database/backups' \
  --exclude='./__pycache__' \
  --exclude='./.pytest_cache' \
  --exclude='./.venv' \
  --exclude='./venv' \
  --exclude='./node_modules' \
  .
LOG "Бэкап готов: $BACKUP_DIR (env.copy + postgres.dump + files.tar.xz)"

# --- stop ---
if [[ "$SKIP_STOP" != "1" ]]; then
  if [[ "$MODE" == "docker" ]]; then
    LOG "Остановка docker compose..."
    docker compose stop web nginx 2>/dev/null || docker compose stop || true
  elif systemctl list-unit-files 2>/dev/null | grep -q '^nikacrm\.service'; then
    LOG "systemctl stop nikacrm"
    systemctl stop nikacrm || true
  fi
fi

# --- update code (preserve .env / uploads / data) ---
ENV_TMP="$(mktemp)"
cp -a "$ROOT_DIR/.env" "$ENV_TMP"

if [[ -n "$BUNDLE" ]]; then
  [[ -f "$BUNDLE" ]] || die "BUNDLE не найден: $BUNDLE"
  LOG "Распаковка $BUNDLE поверх (без удаления .env/data)"
  case "$BUNDLE" in
    *.tar.gz|*.tgz) tar -xzf "$BUNDLE" -C "$ROOT_DIR" --strip-components=0 ;;
    *.tar.xz) tar -xJf "$BUNDLE" -C "$ROOT_DIR" ;;
    *.zip)
      require_cmd unzip
      unzip -qo "$BUNDLE" -d "$ROOT_DIR"
      ;;
    *) die "неизвестный формат BUNDLE (ожидается .tar.gz / .tar.xz / .zip)" ;;
  esac
  cp -a "$ENV_TMP" "$ROOT_DIR/.env"
elif [[ -d "$ROOT_DIR/.git" ]]; then
  require_cmd git
  if [[ -z "$REF" ]]; then
    if git remote get-url origin 2>/dev/null | grep -qi 'Nika-Service-CRM'; then
      REF="main"
    else
      REF="master"
    fi
  fi
  LOG "git fetch + merge --ff-only origin/$REF"
  git fetch --prune origin
  git merge --ff-only "origin/${REF}" || die "ff-only не удался (есть локальные коммиты/конфликты). Откат: см. $BACKUP_DIR"
  cp -a "$ENV_TMP" "$ROOT_DIR/.env"
else
  die "нет .git и не задан BUNDLE — нечем обновлять код"
fi
rm -f "$ENV_TMP"
chmod 600 "$ROOT_DIR/.env" 2>/dev/null || true

# --- deps ---
if [[ "$MODE" == "docker" ]]; then
  LOG "docker compose build"
  docker compose build
else
  VENV_BIN=""
  if [[ -x "$ROOT_DIR/venv/bin/pip" ]]; then VENV_BIN="$ROOT_DIR/venv/bin"
  elif [[ -x "$ROOT_DIR/.venv/bin/pip" ]]; then VENV_BIN="$ROOT_DIR/.venv/bin"
  fi
  [[ -n "$VENV_BIN" ]] || die "venv не найден"
  LOG "pip install -r requirements.txt"
  "$VENV_BIN/pip" install -q --upgrade pip
  "$VENV_BIN/pip" install -q -r "$ROOT_DIR/requirements.txt"
fi

# --- migrations (НЕ bootstrap SQL) ---
LOG "Миграции БД (run_migrations.py) — данные клиентов сохраняются"
if [[ "$MODE" == "docker" ]]; then
  docker compose run --rm --no-deps web python scripts/run_migrations.py \
    || docker compose exec -T web python scripts/run_migrations.py \
    || LOG "WARN: миграции через compose не выполнились — проверьте вручную"
else
  "$VENV_BIN/python" "$ROOT_DIR/scripts/run_migrations.py" || die "миграции упали — см. $BACKUP_DIR"
fi

# --- start ---
if [[ "$SKIP_STOP" != "1" ]]; then
  if [[ "$MODE" == "docker" ]]; then
    LOG "docker compose up -d"
    docker compose up -d
  elif systemctl list-unit-files 2>/dev/null | grep -q '^nikacrm\.service'; then
    LOG "systemctl start nikacrm"
    systemctl start nikacrm
    systemctl is-active --quiet nikacrm || die "nikacrm не активен"
  fi
fi

# --- health ---
sleep 2
if command -v curl >/dev/null 2>&1; then
  if curl -fsS -o /dev/null --max-time 8 "$HEALTH_URL"; then
    LOG "Health OK: $HEALTH_URL"
  else
    LOG "WARN: health-check $HEALTH_URL не ответил (проверьте nginx/порт)"
  fi
fi

LOG "Готово. Архив на случай отката: $BACKUP_DIR"
LOG "Не запускайте ubuntu_2404_bootstrap.sh на живой БД — он перезаписывает .env."
