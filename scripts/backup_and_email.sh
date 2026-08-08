#!/usr/bin/env bash
# Название: backup_and_email
# Назначение: Ежедневный бэкап PostgreSQL + файлов сайта/проекта и отправка архива на email.
# Режимы: Docker Compose (WORK) или host Postgres + systemd (DEMO / self-hosted).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RECIPIENT_EMAIL="${1:-smelkov2008@yandex.ru}"
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
require_cmd pg_dump

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

MODE="$(detect_mode)"
log "START backup job (recipient=$RECIPIENT_EMAIL, mode=$MODE)"

load_env_file

DB_DUMP_FILE="$TMP_DIR/postgres_${TS}.dump"
ARCHIVE_FILE="$BACKUP_DIR/crm_full_backup_${HOSTNAME_SHORT}_${TS}.tar.xz"
SITE_BUNDLE="$TMP_DIR/site_extra_${TS}.tar"

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
  DATABASE_URL="${DATABASE_URL:-}"
  if [[ -z "$DATABASE_URL" ]]; then
    log "ERROR: DATABASE_URL не задан (host mode)"
    exit 2
  fi
  log "Create PostgreSQL dump (host) -> $DB_DUMP_FILE"
  pg_dump --format=custom --file="$DB_DUMP_FILE" "$DATABASE_URL"

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

# Доп. файлы сайта (html/downloads/nginx), если пути существуют
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
# Типовые пути DEMO, если не заданы явно
if [[ ${#EXTRA_LIST[@]} -eq 0 ]]; then
  for p in /var/www/nikacrm-downloads /var/www/html /etc/nginx/sites-enabled/nikacrm.conf; do
    [[ -e "$p" ]] && EXTRA_LIST+=("$p")
  done
fi

if [[ ${#EXTRA_LIST[@]} -gt 0 ]]; then
  log "Bundle site extras -> $SITE_BUNDLE (${#EXTRA_LIST[@]} paths)"
  # Не тащим офлайн-установщики Windows (сотни МБ) — только html/конфиги и мелкие файлы.
  tar -cf "$SITE_BUNDLE" \
    --exclude='*.exe' \
    --exclude='*.EXE' \
    --exclude='*.msi' \
    --exclude='*.zip' \
    "${EXTRA_LIST[@]}"
else
  SITE_BUNDLE=""
fi

log "Create compressed full archive -> $ARCHIVE_FILE"
# На малых VPS (DEMO ~1GB) xz -9e убивается OOM; задайте BACKUP_XZ_OPTS при необходимости.
if [[ -z "${BACKUP_XZ_OPTS:-}" ]]; then
  mem_mb="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
  if [[ "$mem_mb" -gt 0 && "$mem_mb" -lt 2048 ]]; then
    BACKUP_XZ_OPTS="-6 -T1"
    log "Low memory (${mem_mb}MiB): using xz $BACKUP_XZ_OPTS"
  else
    BACKUP_XZ_OPTS="-9e -T0"
  fi
fi
TAR_ARGS=(
  -I "xz $BACKUP_XZ_OPTS" -cf "$ARCHIVE_FILE"
  -C "$TMP_DIR" "$(basename "$DB_DUMP_FILE")"
)
if [[ -n "$SITE_BUNDLE" && -f "$SITE_BUNDLE" ]]; then
  TAR_ARGS+=(-C "$TMP_DIR" "$(basename "$SITE_BUNDLE")")
fi
TAR_ARGS+=(
  -C "$ROOT_DIR"
  --exclude='./.git'
  --exclude='./.cursor'
  --exclude='./data/database/backups'
  --exclude='./data/logs'
  --exclude='./__pycache__'
  --exclude='./.pytest_cache'
  --exclude='./.venv'
  --exclude='./venv'
  --exclude='./packaging/windows/assets'
  --exclude='./packaging/windows/output'
  --exclude='./static/cdn'
  --exclude='*.exe'
  --exclude='*.EXE'
  .
)
tar "${TAR_ARGS[@]}"

ARCHIVE_SIZE_HR="$(du -h "$ARCHIVE_FILE" | awk '{print $1}')"
log "Archive ready: $ARCHIVE_FILE ($ARCHIVE_SIZE_HR)"

export BACKUP_EMAIL_TO="$RECIPIENT_EMAIL"
export BACKUP_ARCHIVE_PATH="$ARCHIVE_FILE"
export BACKUP_TS="$TS"
export BACKUP_HOST="$HOSTNAME_SHORT"
export BACKUP_SIZE="$ARCHIVE_SIZE_HR"
export BACKUP_ARCHIVE_BASENAME="$(basename "$ARCHIVE_FILE")"
export SMTP_SERVER SMTP_PORT SMTP_USE_TLS SMTP_USE_SSL SMTP_USERNAME SMTP_PASSWORD SMTP_SENDER

log "Send archive via SMTP ($SMTP_SERVER:$SMTP_PORT) -> $RECIPIENT_EMAIL"

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
backup_ts = os.environ.get("BACKUP_TS", "")
backup_host = os.environ.get("BACKUP_HOST", "vps")
backup_size = os.environ.get("BACKUP_SIZE", "")

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

# Envelope From — только ASCII mailbox; display name не в envelope
smtp_sender = _ascii_or_empty(smtp_sender) or _ascii_or_empty(smtp_user)
smtp_user = _ascii_or_empty(smtp_user) or smtp_sender
low = smtp_sender.lower()
if low.endswith("@example.com") or low.endswith("@example.org") or "service-center.local" in low:
    smtp_sender = smtp_user

if not archive_path.exists():
    raise FileNotFoundError(f"Archive not found: {archive_path}")

msg = EmailMessage()
msg["Subject"] = f"[CRM Backup] {backup_host} {backup_ts}"
msg["From"] = smtp_sender
msg["To"] = email_to
msg.set_content(
    f"Автоматический бэкап CRM / сайта.\n"
    f"Сервер: {backup_host}\n"
    f"Время: {backup_ts}\n"
    f"Размер архива: {backup_size}\n"
    f"Файл: {archive_path.name}\n"
    f"Содержимое: PostgreSQL dump (-Fc) + дерево проекта (templates/static/docs/…) "
    f"+ доп. пути сайта (downloads/nginx), если есть.\n"
)

with archive_path.open("rb") as f:
    msg.add_attachment(
        f.read(),
        maintype="application",
        subtype="xz",
        filename=archive_path.name,
    )

if use_ssl:
    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=120) as server:
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
else:
    with smtplib.SMTP(smtp_server, smtp_port, timeout=120) as server:
        if use_tls:
            server.starttls()
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
print("OK")
PY
}

if [[ "$MODE" == "docker" ]]; then
  # Предпочитаем host python (архив на хосте); fallback — контейнер web с volume path
  if ! send_via_python; then
    log "WARN: host SMTP send failed, trying docker web..."
    docker compose exec -T \
      -e BACKUP_EMAIL_TO \
      -e BACKUP_TS \
      -e BACKUP_HOST \
      -e BACKUP_SIZE \
      -e BACKUP_ARCHIVE_BASENAME \
      -e SMTP_SERVER -e SMTP_PORT -e SMTP_USE_TLS -e SMTP_USE_SSL \
      -e SMTP_USERNAME -e SMTP_PASSWORD -e SMTP_SENDER \
      web python - <<'PY'
import os, smtplib
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
archive_path = Path("/app/database/backups/auto") / os.environ["BACKUP_ARCHIVE_BASENAME"]
os.environ["BACKUP_ARCHIVE_PATH"] = str(archive_path)
# reuse same logic via inline minimal send
smtp_server = os.environ["SMTP_SERVER"].strip()
smtp_port = int(os.environ.get("SMTP_PORT") or "587")
smtp_user = os.environ.get("SMTP_USERNAME", "").strip()
smtp_password = os.environ.get("SMTP_PASSWORD", "")
smtp_sender = os.environ.get("SMTP_SENDER", "").strip() or smtp_user
_, se = parseaddr(smtp_sender); smtp_sender = se or smtp_sender
_, su = parseaddr(smtp_user); smtp_user = su or smtp_user or smtp_sender
use_tls = str(os.environ.get("SMTP_USE_TLS", "true")).lower() in {"1","true","yes","on","t"}
use_ssl = str(os.environ.get("SMTP_USE_SSL", "false")).lower() in {"1","true","yes","on","t"}
msg = EmailMessage()
msg["Subject"] = f"[CRM Backup] {os.environ.get('BACKUP_HOST')} {os.environ.get('BACKUP_TS')}"
msg["From"] = smtp_sender
msg["To"] = os.environ["BACKUP_EMAIL_TO"]
msg.set_content(f"Backup {archive_path.name} size={os.environ.get('BACKUP_SIZE')}\n")
with archive_path.open("rb") as f:
    msg.add_attachment(f.read(), maintype="application", subtype="xz", filename=archive_path.name)
if use_ssl:
    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=120) as s:
        s.login(smtp_user, smtp_password); s.send_message(msg)
else:
    with smtplib.SMTP(smtp_server, smtp_port, timeout=120) as s:
        if use_tls: s.starttls()
        s.login(smtp_user, smtp_password); s.send_message(msg)
PY
  fi
else
  send_via_python
fi

log "Email sent successfully"

log "Cleanup old auto backups (> ${RETENTION_DAYS} days)"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'crm_full_backup_*.tar.xz' -mtime +"$RETENTION_DAYS" -delete

log "DONE backup job"
