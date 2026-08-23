#!/usr/bin/env bash
# Название: backup_and_email
# Назначение: Полный снимок CRM в два письма: data (dump + uploads + .env) и files (дерево без git/venv).
# Режимы: Docker Compose или host Postgres + systemd (self-hosted).
# Получатель: argv $1, иначе BACKUP_EMAIL_TO, иначе MAIL_USERNAME из .env.
# Не зашивать личную почту и IP сервера — скрипт уходит в публичный OSS.
# Вложение ≤ 28 МБ; крупнее — тома 7z по 25 МБ (*_mail.7z.001). Целый .7z остаётся на диске.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
HOSTNAME_SHORT="$(hostname -s 2>/dev/null || echo vps)"
TS="$(date +%Y%m%d_%H%M%S)"

BACKUP_DIR="$ROOT_DIR/data/database/backups/auto"
TMP_DIR="$BACKUP_DIR/tmp_$TS"
LOG_DIR="$ROOT_DIR/data/logs"
LOG_FILE="$LOG_DIR/backup_email.log"
# Доп. пути сайта (nginx downloads, html) — через пробел/перевод строки в BACKUP_EXTRA_PATHS
BACKUP_EXTRA_PATHS="${BACKUP_EXTRA_PATHS:-}"

mkdir -p "$BACKUP_DIR" "$TMP_DIR" "$LOG_DIR"

log() {
  local msg="$1"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg" | tee -a "$LOG_FILE"
}

cleanup_tmp() {
  rm -rf "$TMP_DIR" 2>/dev/null || true
}
trap cleanup_tmp EXIT

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "ERROR: Команда '$cmd' не найдена"
    exit 2
  fi
}

require_cmd tar
require_cmd xz
require_cmd python3
if command -v 7z >/dev/null 2>&1; then
  SEVENZ_BIN="7z"
elif command -v 7za >/dev/null 2>&1; then
  SEVENZ_BIN="7za"
else
  log "ERROR: 7z не найден (apt install p7zip-full)"
  exit 2
fi
# Host pg_dump/psql нужны только в mode=host. В Docker dump идёт
# через `docker compose exec postgres pg_dump` — клиент на хосте не обязателен.

assert_pg_custom_dump() {
  local dump_path="$1"
  local min_bytes="${2:-512}"
  if [[ ! -s "$dump_path" ]]; then
    log "ERROR: PostgreSQL dump missing or empty: $dump_path"
    exit 2
  fi
  if ! python3 -c 'import sys; sys.exit(0 if open(sys.argv[1],"rb").read(5)==b"PGDMP" else 1)' "$dump_path"; then
    log "ERROR: dump is not pg_dump custom format (-Fc): $dump_path"
    exit 2
  fi
  local dump_bytes
  dump_bytes="$(wc -c < "$dump_path" | tr -d ' ')"
  if [[ "$dump_bytes" -lt "$min_bytes" ]]; then
    log "ERROR: dump too small (${dump_bytes} bytes): $dump_path"
    exit 2
  fi
  log "PostgreSQL dump OK (${dump_bytes} bytes, custom format)"
}

LOCK_FILE="${BACKUP_LOCK_FILE:-$BACKUP_DIR/backup_and_email.lock}"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "Skip: another backup_and_email is running"
  exit 0
fi

detect_mode() {
  if [[ -n "${BACKUP_MODE:-}" ]]; then
    echo "$BACKUP_MODE"
    return
  fi
  if command -v docker >/dev/null 2>&1 && docker compose ps >/dev/null 2>&1; then
    if docker compose ps --status running --services 2>/dev/null | grep -qx postgres; then
      echo docker
      return
    fi
  fi
  echo host
}

load_env_file() {
  # Безопасный разбор .env без source (значения с пробелами/@private и т.п.)
  # Экспортируем только нужные ключи в текущий bash-процесс.
  local export_file
  export_file="$(mktemp)"
  python3 - "$export_file" <<'PY'
from pathlib import Path
import shlex
import sys
out = Path(sys.argv[1])
wanted = {
    "DATABASE_URL",
    "MAIL_SERVER",
    "MAIL_PORT",
    "MAIL_USE_TLS",
    "MAIL_USE_SSL",
    "MAIL_USERNAME",
    "MAIL_PASSWORD",
    "MAIL_DEFAULT_SENDER",
    "BACKUP_EXTRA_PATHS",
    "BACKUP_RETENTION_DAYS",
    "BACKUP_MODE",
    "BACKUP_ARCHIVE_PASSWORD",
    "BACKUP_PUSH_PRIVATE",
    "BACKUP_EMAIL_TO",
    "BACKUP_SITE_LABEL",
    "BACKUP_FORCE",
}
lines = []
path = Path(".env")
if path.exists():
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, val = raw.split("=", 1)
        key = key.strip()
        if key not in wanted:
            continue
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        lines.append(f"export {key}={shlex.quote(val)}")
out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
PY
  # shellcheck disable=SC1090
  source "$export_file"
  rm -f "$export_file"
}

load_env_file
MODE="$(detect_mode)"
if [[ -n "${1:-}" ]]; then
  RECIPIENT_EMAIL="$1"
elif [[ -n "${BACKUP_EMAIL_TO:-}" ]]; then
  RECIPIENT_EMAIL="$BACKUP_EMAIL_TO"
else
  RECIPIENT_EMAIL="${MAIL_USERNAME:-}"
fi
if [[ -z "$RECIPIENT_EMAIL" ]]; then
  log "ERROR: укажите получателя: $0 you@example.com  (или BACKUP_EMAIL_TO / MAIL_USERNAME в .env)"
  exit 2
fi
log "START backup job (recipient=$RECIPIENT_EMAIL, mode=$MODE)"

STAMP_FILE="${BACKUP_STAMP_FILE:-$BACKUP_DIR/.last_ok_day}"
TODAY="$(date +%F)"
if [[ "${BACKUP_FORCE:-}" != "1" && -f "$STAMP_FILE" && "$(tr -d '[:space:]' < "$STAMP_FILE")" == "$TODAY" ]]; then
  log "Skip: already completed successfully on $TODAY (BACKUP_FORCE=1 to override)"
  exit 0
fi

DB_DUMP_FILE="$TMP_DIR/postgres_${TS}.dump"

if [[ "$MODE" == "docker" ]]; then
  require_cmd docker
  if ! docker compose ps >/dev/null 2>&1; then
    log "ERROR: docker compose недоступен в $ROOT_DIR"
    exit 2
  fi
  PG_USER="$(docker compose exec -T postgres printenv POSTGRES_USER | tr -d '\r' || true)"
  PG_DB="$(docker compose exec -T postgres printenv POSTGRES_DB | tr -d '\r' || true)"
  if [[ -z "$PG_USER" || -z "$PG_DB" ]]; then
    log "ERROR: Не удалось определить POSTGRES_USER/POSTGRES_DB"
    exit 2
  fi
  log "Create PostgreSQL dump (docker) -> $DB_DUMP_FILE"
  docker compose exec -T postgres pg_dump -U "$PG_USER" -d "$PG_DB" -Fc > "$DB_DUMP_FILE"
  assert_pg_custom_dump "$DB_DUMP_FILE"

  SMTP_LINE="$(
    docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -At -F $'\t' -c "
      SELECT
        COALESCE(mail_server, ''),
        COALESCE(mail_port::text, ''),
        COALESCE(mail_use_tls::text, ''),
        COALESCE(mail_use_ssl::text, ''),
        COALESCE(mail_username, ''),
        COALESCE(mail_password, ''),
        COALESCE(mail_default_sender, '')
      FROM general_settings
      ORDER BY id
      LIMIT 1;
    " | tr -d '\r'
  )"
  IFS=$'\t' read -r SMTP_SERVER SMTP_PORT SMTP_USE_TLS SMTP_USE_SSL SMTP_USERNAME SMTP_PASSWORD SMTP_SENDER <<<"$SMTP_LINE"

  WEB_MAIL_ENV="$(
    docker compose exec -T web python -c "import os; print('\\t'.join([
      os.getenv('MAIL_SERVER',''),
      os.getenv('MAIL_PORT',''),
      os.getenv('MAIL_USE_TLS',''),
      os.getenv('MAIL_USE_SSL',''),
      os.getenv('MAIL_USERNAME',''),
      os.getenv('MAIL_PASSWORD',''),
      os.getenv('MAIL_DEFAULT_SENDER',''),
    ]))" | tr -d '\r'
  )"
  IFS=$'\t' read -r WEB_MAIL_SERVER WEB_MAIL_PORT WEB_MAIL_USE_TLS WEB_MAIL_USE_SSL WEB_MAIL_USERNAME WEB_MAIL_PASSWORD WEB_MAIL_SENDER <<<"$WEB_MAIL_ENV"
else
  require_cmd pg_dump
  require_cmd psql
  DATABASE_URL="${DATABASE_URL:-}"
  if [[ -z "$DATABASE_URL" ]]; then
    log "ERROR: DATABASE_URL не задан (host mode)"
    exit 2
  fi
  log "Create PostgreSQL dump (host) -> $DB_DUMP_FILE"
  pg_dump --format=custom --file="$DB_DUMP_FILE" "$DATABASE_URL"
  assert_pg_custom_dump "$DB_DUMP_FILE"

  SMTP_LINE="$(
    psql "$DATABASE_URL" -At -F $'\t' -c "
      SELECT
        COALESCE(mail_server, ''),
        COALESCE(mail_port::text, ''),
        COALESCE(mail_use_tls::text, ''),
        COALESCE(mail_use_ssl::text, ''),
        COALESCE(mail_username, ''),
        COALESCE(mail_password, ''),
        COALESCE(mail_default_sender, '')
      FROM general_settings
      ORDER BY id
      LIMIT 1;
    " | tr -d '\r'
  )"
  IFS=$'\t' read -r SMTP_SERVER SMTP_PORT SMTP_USE_TLS SMTP_USE_SSL SMTP_USERNAME SMTP_PASSWORD SMTP_SENDER <<<"$SMTP_LINE"
  WEB_MAIL_SERVER="${MAIL_SERVER:-}"
  WEB_MAIL_PORT="${MAIL_PORT:-}"
  WEB_MAIL_USE_TLS="${MAIL_USE_TLS:-}"
  WEB_MAIL_USE_SSL="${MAIL_USE_SSL:-}"
  WEB_MAIL_USERNAME="${MAIL_USERNAME:-}"
  WEB_MAIL_PASSWORD="${MAIL_PASSWORD:-}"
  WEB_MAIL_SENDER="${MAIL_DEFAULT_SENDER:-}"
fi

if [[ -z "${SMTP_SERVER:-}" ]]; then SMTP_SERVER="${WEB_MAIL_SERVER:-}"; fi
if [[ -z "${SMTP_PORT:-}" ]]; then SMTP_PORT="${WEB_MAIL_PORT:-587}"; fi
if [[ -z "${SMTP_USE_TLS:-}" ]]; then SMTP_USE_TLS="${WEB_MAIL_USE_TLS:-true}"; fi
if [[ -z "${SMTP_USE_SSL:-}" ]]; then SMTP_USE_SSL="${WEB_MAIL_USE_SSL:-false}"; fi
if [[ -z "${SMTP_USERNAME:-}" ]]; then SMTP_USERNAME="${WEB_MAIL_USERNAME:-}"; fi
if [[ -z "${SMTP_PASSWORD:-}" ]]; then SMTP_PASSWORD="${WEB_MAIL_PASSWORD:-}"; fi
if [[ -z "${SMTP_SENDER:-}" ]]; then SMTP_SENDER="${WEB_MAIL_SENDER:-$SMTP_USERNAME}"; fi

# Для AUTH всегда предпочитаем MAIL_* из .env (ASCII). В general_settings
# часто кириллический From и иногда «битый» пароль — smtplib LOGIN тогда падает.
# Docker web может не пробросить MAIL_PASSWORD — тогда остаётся пароль из БД с non-ASCII.
if [[ -n "${MAIL_USERNAME:-}" ]]; then
  SMTP_USERNAME="$MAIL_USERNAME"
  WEB_MAIL_USERNAME="$MAIL_USERNAME"
fi
if [[ -n "${MAIL_PASSWORD:-}" ]]; then
  SMTP_PASSWORD="$MAIL_PASSWORD"
  WEB_MAIL_PASSWORD="$MAIL_PASSWORD"
fi
if [[ -n "${MAIL_SERVER:-}" ]]; then
  SMTP_SERVER="$MAIL_SERVER"
  WEB_MAIL_SERVER="$MAIL_SERVER"
fi
if [[ -n "${MAIL_PORT:-}" ]]; then
  SMTP_PORT="$MAIL_PORT"
  WEB_MAIL_PORT="$MAIL_PORT"
fi
if [[ -n "${MAIL_DEFAULT_SENDER:-}" ]]; then
  SMTP_SENDER="$MAIL_DEFAULT_SENDER"
  WEB_MAIL_SENDER="$MAIL_DEFAULT_SENDER"
elif [[ -n "${WEB_MAIL_SENDER:-}" ]]; then
  SMTP_SENDER="$WEB_MAIL_SENDER"
fi
# From: только mailbox ASCII (отрежем display name с кириллицей на стороне Python)

# Демо-заглушка noreply@example.com — не использовать как From
case "${SMTP_SENDER,,}" in
  *example.com*|*service-center.local*)
    SMTP_SENDER="$SMTP_USERNAME"
    ;;
esac

if [[ -z "${SMTP_SERVER:-}" || -z "${SMTP_USERNAME:-}" || -z "${SMTP_PASSWORD:-}" || -z "${SMTP_SENDER:-}" ]]; then
  log "ERROR: SMTP не настроен (server/username/password/sender). Задайте в CRM Настройки→Почта или MAIL_* в .env"
  exit 3
fi

# Полный снимок: письмо 1 = data (БД, uploads, портал в Postgres), письмо 2 = files.
SITE_LABEL="${BACKUP_SITE_LABEL:-CRM ${HOSTNAME_SHORT}}"

STAGE="$TMP_DIR/payload"
mkdir -p "$STAGE/postgres" "$STAGE/env" "$STAGE/uploads" "$STAGE/nginx" "$STAGE/compose"
cp -a "$DB_DUMP_FILE" "$STAGE/postgres/"
if [[ -f "$ROOT_DIR/.env" ]]; then
  cp -a "$ROOT_DIR/.env" "$STAGE/env/.env"
  chmod 600 "$STAGE/env/.env"
fi
if [[ -d "$ROOT_DIR/data/uploads" ]]; then
  cp -a "$ROOT_DIR/data/uploads/." "$STAGE/uploads/" 2>/dev/null || true
fi
if [[ -d "$ROOT_DIR/data/monitoring" ]]; then
  mkdir -p "$STAGE/monitoring"
  cp -a "$ROOT_DIR/data/monitoring/." "$STAGE/monitoring/" 2>/dev/null || true
fi
if git -C "$ROOT_DIR" rev-parse HEAD >/dev/null 2>&1; then
  git -C "$ROOT_DIR" rev-parse HEAD > "$STAGE/GIT_HEAD"
  git -C "$ROOT_DIR" rev-parse --abbrev-ref HEAD > "$STAGE/GIT_BRANCH" 2>/dev/null || true
  git -C "$ROOT_DIR" remote get-url origin > "$STAGE/GIT_REMOTE" 2>/dev/null || true
fi
[[ -f "$ROOT_DIR/docker/docker-compose.yml" ]] && cp -a "$ROOT_DIR/docker/docker-compose.yml" "$STAGE/compose/"
[[ -f "$ROOT_DIR/docker-compose.yml" ]] && cp -a "$ROOT_DIR/docker-compose.yml" "$STAGE/compose/"

for f in \
  /etc/nginx/conf.d/crm.conf \
  /etc/nginx/conf.d/00-crm-timed-log.conf \
  /etc/nginx/conf.d/00-nika-security-limits.conf \
  /etc/nginx/conf.d/ssl_servers_inc.conf
do
  [[ -f "$f" ]] && cp -a "$f" "$STAGE/nginx/"
done
if [[ -d /etc/letsencrypt/live ]]; then
  mkdir -p "$STAGE/letsencrypt"
  tar -C /etc -cf - letsencrypt | tar -C "$STAGE" -xf -
fi

EXTRA_LIST=()
if [[ -n "${BACKUP_EXTRA_PATHS// }" ]]; then
  # shellcheck disable=SC2206
  EXTRA_CANDIDATES=($BACKUP_EXTRA_PATHS)
  for p in "${EXTRA_CANDIDATES[@]}"; do
    if [[ -e "$p" ]]; then
      EXTRA_LIST+=("$p")
    else
      log "WARN: extra path missing: $p"
    fi
  done
fi
if [[ ${#EXTRA_LIST[@]} -gt 0 ]]; then
  mkdir -p "$STAGE/extra"
  tar -C / -cf - \
    --exclude='*.exe' --exclude='*.EXE' --exclude='*.msi' --exclude='*.zip' \
    "${EXTRA_LIST[@]#/}" 2>/dev/null \
    | tar -C "$STAGE/extra" -xf - || log "WARN: extra paths pack failed"
fi

DUMP_BYTES="$(wc -c < "$DB_DUMP_FILE" | tr -d ' ')"
DUMP_NAME="$(basename "$DB_DUMP_FILE")"
{
  echo "label=$SITE_LABEL"
  echo "created=$(date -Is)"
  echo "host=$(hostname -f 2>/dev/null || hostname)"
  echo "mode=$MODE"
  echo "purpose=full snapshot; data letter + files letter; restore without git"
  echo "contents=postgres dump, .env, data/uploads, nginx, letsencrypt, monitoring, RESTORE.sh"
  echo "postgres_dump=$DUMP_NAME"
  echo "postgres_dump_bytes=$DUMP_BYTES"
  echo "files_archive=crm_files_backup_${HOSTNAME_SHORT}_${TS}.7z"
} > "$STAGE/MANIFEST.txt"

cat > "$STAGE/RESTORE.txt" <<EOF
Полный снимок WORK — два архива
================================
Пароль 7z: BACKUP_ARCHIVE_PASSWORD / credentials.txt (в письме нет).
Не нужен git: код в письме 2 (crm_files_backup_*.7z).

7z x crm_data_backup_*.7z
7z x crm_files_backup_*.7z
tar -xJf crm_data_backup_*.tar.xz
tar -xJf crm_files_backup_*.tar.xz
sudo bash payload/RESTORE.sh /opt/nikanewcrm

Дамп: postgres/$DUMP_NAME (${DUMP_BYTES} байт, custom -Fc). Портал клиентов — в этой же БД.
Не делать: docker compose down -v
EOF

cat > "$STAGE/RESTORE.sh" <<'RESTORE_SH'
#!/usr/bin/env bash
# Restore WORK CRM from unpacked data (payload/) + files/ archives.
set -euo pipefail
DEST="${1:-/opt/nikanewcrm}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES=""
if [[ -d "$HERE/../files" ]]; then
  FILES="$(cd "$HERE/../files" && pwd)"
elif [[ -d "$HERE/files" ]]; then
  FILES="$HERE/files"
fi

mkdir -p "$DEST"
if [[ -n "$FILES" ]]; then
  echo "Copy application files -> $DEST"
  cp -a "$FILES"/. "$DEST"/
fi
if [[ -f "$HERE/env/.env" ]]; then
  cp -a "$HERE/env/.env" "$DEST/.env"
  chmod 600 "$DEST/.env"
fi
if [[ -d "$HERE/uploads" ]]; then
  mkdir -p "$DEST/data/uploads"
  cp -a "$HERE/uploads"/. "$DEST/data/uploads"/
fi
if [[ -d "$HERE/monitoring" ]]; then
  mkdir -p "$DEST/data/monitoring"
  cp -a "$HERE/monitoring"/. "$DEST/data/monitoring"/
fi
if [[ -d "$HERE/letsencrypt" && -d /etc ]]; then
  mkdir -p /etc/letsencrypt
  cp -a "$HERE/letsencrypt"/. /etc/letsencrypt/ 2>/dev/null || true
fi
if [[ -d "$HERE/nginx" && -d /etc/nginx/conf.d ]]; then
  cp -an "$HERE/nginx"/. /etc/nginx/conf.d/ 2>/dev/null || true
fi

cd "$DEST"
if [[ -f docker-compose.yml ]]; then
  dc() { docker compose "$@"; }
elif [[ -f docker/docker-compose.yml ]]; then
  dc() { docker compose -f docker/docker-compose.yml "$@"; }
else
  echo "ERROR: docker-compose.yml not found in $DEST" >&2
  exit 2
fi

echo "Start postgres (never: docker compose down -v)"
dc up -d postgres
ok=0
for _ in $(seq 1 40); do
  if dc exec -T postgres pg_isready >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done
if [[ "$ok" != "1" ]]; then
  echo "ERROR: postgres is not ready" >&2
  exit 2
fi

DUMP="$(ls -1 "$HERE"/postgres/*.dump 2>/dev/null | head -1 || true)"
if [[ -z "$DUMP" ]]; then
  echo "ERROR: no postgres/*.dump in payload" >&2
  exit 2
fi
PG_USER="$(dc exec -T postgres printenv POSTGRES_USER | tr -d '\r')"
PG_DB="$(dc exec -T postgres printenv POSTGRES_DB | tr -d '\r')"
echo "Restore $DUMP -> $PG_DB"
set +e
dc exec -T postgres pg_restore -U "$PG_USER" -d "$PG_DB" --clean --if-exists < "$DUMP"
rc=$?
set -e
if [[ $rc -gt 1 ]]; then
  echo "ERROR: pg_restore failed (rc=$rc)" >&2
  exit 2
fi

dc up -d
echo "OK: restore finished. Open /login. Do not run docker compose down -v."
RESTORE_SH
chmod 755 "$STAGE/RESTORE.sh"

log "Pack application files (exclude git/venv/backups/uploads)"
FILES_STAGE="$TMP_DIR/files"
mkdir -p "$FILES_STAGE"
tar -C "$ROOT_DIR" \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='.venv-win' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='data/database/backups' \
  --exclude='data/uploads' \
  --exclude='data/monitoring' \
  -cf - . | tar -C "$FILES_STAGE" -xf -

if [[ -z "${BACKUP_XZ_OPTS:-}" ]]; then
  mem_mb="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
  if [[ "$mem_mb" -gt 0 && "$mem_mb" -lt 2048 ]]; then
    BACKUP_XZ_OPTS="-6 -T1"
    log "Low memory (${mem_mb}MiB): using xz $BACKUP_XZ_OPTS"
  else
    BACKUP_XZ_OPTS="-9e -T0"
  fi
fi

DATA_TAR="$BACKUP_DIR/crm_data_backup_${HOSTNAME_SHORT}_${TS}.tar.xz"
FILES_TAR="$BACKUP_DIR/crm_files_backup_${HOSTNAME_SHORT}_${TS}.tar.xz"
log "Create compressed data archive -> $DATA_TAR"
tar -I "xz $BACKUP_XZ_OPTS" -cf "$DATA_TAR" -C "$TMP_DIR" payload
log "Create compressed files archive -> $FILES_TAR"
tar -I "xz $BACKUP_XZ_OPTS" -cf "$FILES_TAR" -C "$TMP_DIR" files

if [[ -z "${BACKUP_ARCHIVE_PASSWORD:-}" ]]; then
  log "ERROR: BACKUP_ARCHIVE_PASSWORD пуст в .env — открытый дамп на почту не шлём"
  rm -f "$DATA_TAR" "$FILES_TAR"
  exit 2
fi

# Mail attachment cap. Larger .7z is kept whole on disk; email gets 25MB volumes.
ATTACH_MAX="${BACKUP_ATTACH_MAX_BYTES:-28000000}"
VOLUME_BYTES="${BACKUP_7Z_VOLUME_BYTES:-25000000}"

pack_7z_one() {
  local src="$1" dest="$2"
  rm -f "$dest"
  local rc=0
  set +e
  (
    cd "$(dirname "$src")" || exit 2
    "$SEVENZ_BIN" a -t7z -mx=0 -mhe=on -y \
      "-p${BACKUP_ARCHIVE_PASSWORD}" "$dest" "$(basename "$src")" >/dev/null
  )
  rc=$?
  set -e
  if [[ $rc -gt 1 || ! -f "$dest" ]]; then
    log "ERROR: 7z failed for $src (rc=$rc)"
    exit 2
  fi
}

split_7z_mail_parts() {
  local src="$1" dest="$2"
  local size prefix rc p
  size="$(stat -c%s "$dest")"
  WRAP_7Z_PARTS=()
  if [[ "$size" -le "$ATTACH_MAX" ]]; then
    WRAP_7Z_PARTS=("$dest")
    return 0
  fi
  prefix="${dest%.7z}_mail.7z"
  rm -f "${prefix}".[0-9][0-9][0-9]
  leftover="${dest%.7z}_mail.7z"
  [[ -f "$leftover" ]] && rm -f "$leftover"
  log "Archive ${size} > ${ATTACH_MAX}: split mail volumes ${VOLUME_BYTES}b -> ${prefix}.00N"
  set +e
  (
    cd "$(dirname "$src")" || exit 2
    "$SEVENZ_BIN" a -t7z -mx=0 -mhe=on -y \
      "-v${VOLUME_BYTES}b" \
      "-p${BACKUP_ARCHIVE_PASSWORD}" "$prefix" "$(basename "$src")" >/dev/null
  )
  rc=$?
  set -e
  if [[ $rc -gt 1 ]]; then
    log "ERROR: 7z volume split failed (rc=$rc)"
    exit 2
  fi
  for p in "${prefix}".[0-9][0-9][0-9]; do
    [[ -f "$p" ]] && WRAP_7Z_PARTS+=("$p")
  done
  if [[ ${#WRAP_7Z_PARTS[@]} -eq 0 && -f "$prefix" ]]; then
    WRAP_7Z_PARTS=("$prefix")
  fi
  if [[ ${#WRAP_7Z_PARTS[@]} -eq 0 ]]; then
    log "ERROR: 7z volume split produced no parts"
    exit 2
  fi
}

wrap_7z() {
  local src="$1"
  local dest="${src%.tar.xz}.7z"
  log "7z AES-256 + encrypt headers -> $dest"
  pack_7z_one "$src" "$dest"
  split_7z_mail_parts "$src" "$dest"
  rm -f "$src"
  WRAP_7Z_OUT="$dest"
}

wrap_7z "$DATA_TAR"
DATA_ARCHIVE="$WRAP_7Z_OUT"
DATA_MAIL_PARTS=("${WRAP_7Z_PARTS[@]}")
wrap_7z "$FILES_TAR"
FILES_ARCHIVE="$WRAP_7Z_OUT"
FILES_MAIL_PARTS=("${WRAP_7Z_PARTS[@]}")
DATA_SIZE_HR="$(du -h "$DATA_ARCHIVE" | awk '{print $1}')"
FILES_SIZE_HR="$(du -h "$FILES_ARCHIVE" | awk '{print $1}')"
log "Archives ready: $DATA_ARCHIVE ($DATA_SIZE_HR) + $FILES_ARCHIVE ($FILES_SIZE_HR)"

if [[ "${BACKUP_PUSH_PRIVATE:-}" == "1" ]]; then
  log "Push encrypted data snapshot to private branch work-restore"
  if ! bash "$ROOT_DIR/scripts/backup_push_work_restore.sh" "$DATA_ARCHIVE"; then
    log "WARN: private git snapshot push failed (disk archive still kept)"
  fi
fi

if [[ "${BACKUP_SKIP_EMAIL:-}" == "1" ]]; then
  log "BACKUP_SKIP_EMAIL=1 — archives kept, no mail"
  echo "$TODAY" > "$STAMP_FILE"
  exit 0
fi

export BACKUP_EMAIL_TO="$RECIPIENT_EMAIL"
export BACKUP_TS="$TS"
export BACKUP_HOST="$HOSTNAME_SHORT"
export BACKUP_SITE_LABEL="$SITE_LABEL"
export BACKUP_ATTACH_MAX_BYTES="$ATTACH_MAX"
export SMTP_SERVER SMTP_PORT SMTP_USE_TLS SMTP_USE_SSL SMTP_USERNAME SMTP_PASSWORD SMTP_SENDER

send_via_python() {
  python3 - <<'PY'
import os
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path

smtp_server = os.environ["SMTP_SERVER"].strip()
smtp_port = int(os.environ.get("SMTP_PORT") or "587")
smtp_user_raw = os.environ.get("SMTP_USERNAME", "").strip()
smtp_password = os.environ.get("SMTP_PASSWORD", "")
smtp_sender_raw = os.environ.get("SMTP_SENDER", "").strip() or smtp_user_raw
use_tls = str(os.environ.get("SMTP_USE_TLS", "true")).strip().lower() in {"1", "true", "yes", "on", "t"}
use_ssl = str(os.environ.get("SMTP_USE_SSL", "false")).strip().lower() in {"1", "true", "yes", "on", "t"}
email_to = os.environ["BACKUP_EMAIL_TO"].strip()
archive_path = Path(os.environ["BACKUP_ARCHIVE_PATH"])
backup_host = os.environ.get("BACKUP_HOST", "vps")

_, sender_email = parseaddr(smtp_sender_raw)
smtp_sender = (sender_email or smtp_sender_raw).strip()
_, smtp_user_email = parseaddr(smtp_user_raw)
smtp_user = (smtp_user_email or smtp_user_raw).strip() or smtp_sender

def _ascii_or_empty(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    try:
        v.encode("ascii")
        return v
    except UnicodeEncodeError:
        return ""

smtp_sender = _ascii_or_empty(smtp_sender) or _ascii_or_empty(smtp_user)
smtp_user = _ascii_or_empty(smtp_user) or smtp_sender
try:
    smtp_password.encode("ascii")
except UnicodeEncodeError as exc:
    raise SystemExit(f"SMTP password has non-ASCII bytes: {exc}") from exc
if not smtp_user or not smtp_password:
    raise SystemExit("SMTP username/password empty after ASCII normalize")
low = smtp_sender.lower()
if low.endswith("@example.com") or low.endswith("@example.org") or "service-center.local" in low:
    smtp_sender = smtp_user

if not archive_path.exists():
    raise FileNotFoundError(f"Archive not found: {archive_path}")

msg = EmailMessage()
msg["Subject"] = os.environ["BACKUP_SUBJECT"]
msg["From"] = smtp_sender
msg["To"] = email_to
body = os.environ["BACKUP_BODY"]
attach_max = int(os.environ.get("BACKUP_ATTACH_MAX_BYTES") or "28000000")
size_bytes = archive_path.stat().st_size
if size_bytes > attach_max:
    body += (
        f"\nВложение НЕ приложено (размер {size_bytes} > {attach_max}).\n"
        f"Файл на сервере: {archive_path}\n"
        f"scp root@{backup_host}:{archive_path} .\n"
    )
msg.set_content(body)
if size_bytes <= attach_max:
    with archive_path.open("rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="x-7z-compressed",
            filename=archive_path.name,
        )

if use_ssl:
    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=180) as server:
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
else:
    with smtplib.SMTP(smtp_server, smtp_port, timeout=180) as server:
        if use_tls:
            server.starttls()
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
print("OK")
PY
}

send_archive_mail() {
  local archive="$1" subject="$2" body="$3"
  export BACKUP_ARCHIVE_PATH="$archive"
  export BACKUP_SUBJECT="$subject"
  export BACKUP_BODY="$body"
  export BACKUP_SIZE
  BACKUP_SIZE="$(du -h "$archive" | awk '{print $1}')"
  log "Send $archive ($BACKUP_SIZE) via SMTP ($SMTP_SERVER:$SMTP_PORT) -> $RECIPIENT_EMAIL"
  send_via_python
}

send_mail_parts() {
  local subject_base="$1" body_base="$2"
  shift 2
  local parts=("$@")
  local n="${#parts[@]}" i=1 p names="" extra subject
  for p in "${parts[@]}"; do
    names+="$(basename "$p") "
  done
  names="${names%% }"
  for p in "${parts[@]}"; do
    extra=""
    subject="$subject_base"
    if [[ "$n" -gt 1 ]]; then
      subject="${subject_base} ${i}/${n}"
      extra="
Часть ${i}/${n}. Положите ВСЕ части в одну папку и откройте первую:
  7z x $(basename "${parts[0]}")
Файлы: ${names}
"
    fi
    send_archive_mail "$p" "$subject" "${body_base}${extra}"
    i=$((i + 1))
  done
}

send_mail_parts \
  "[CRM Snapshot] ${SITE_LABEL} data ${TS}" \
  "Полный снимок CRM — ДАННЫЕ.

Сайт: ${SITE_LABEL}
Сервер: ${HOSTNAME_SHORT}
Время: ${TS}
Целый архив на диске: $(basename "$DATA_ARCHIVE") (${DATA_SIZE_HR})

В архиве: PostgreSQL dump (заявки, клиенты, личный кабинет),
.env, загрузки (фото), nginx, Let's Encrypt, мониторинг,
RESTORE.sh + RESTORE.txt.

Отдельно придут файлы приложения (crm_files_backup_*).
Пароль 7z: BACKUP_ARCHIVE_PASSWORD / credentials.txt, в письме нет.
7z x *.7z (или *.7z.001) && tar -xJf crm_*_*.tar.xz
sudo bash payload/RESTORE.sh /opt/nikanewcrm
" \
  "${DATA_MAIL_PARTS[@]}"

send_mail_parts \
  "[CRM Snapshot] ${SITE_LABEL} files ${TS}" \
  "Полный снимок CRM — ФАЙЛЫ.

Сайт: ${SITE_LABEL}
Сервер: ${HOSTNAME_SHORT}
Время: ${TS}
Целый архив на диске: $(basename "$FILES_ARCHIVE") (${FILES_SIZE_HR})

В архиве: дерево приложения (app, templates, static, docker, docs)
без .git, venv, node_modules и без старых бэкапов.
Uploads и база — в письмах data.

Пароль 7z тот же. Restore: payload/RESTORE.sh из письма data.
" \
  "${FILES_MAIL_PARTS[@]}"

log "Emails sent successfully"
echo "$TODAY" > "$STAMP_FILE"

log "Cleanup old auto backups (> ${RETENTION_DAYS} days)"
find "$BACKUP_DIR" -maxdepth 1 -type f \( \
  -name 'crm_full_backup_*.tar.xz' -o -name 'crm_full_backup_*.tar.xz.enc' \
  -o -name 'crm_data_backup_*.tar.xz' -o -name 'crm_data_backup_*.tar.xz.enc' \
  -o -name 'crm_data_backup_*.7z' -o -name 'crm_data_backup_*_mail.7z.*' \
  -o -name 'crm_files_backup_*.tar.xz' -o -name 'crm_files_backup_*.7z' \
  -o -name 'crm_files_backup_*_mail.7z.*' \
\) -mtime +"$RETENTION_DAYS" -delete

log "DONE backup job"
