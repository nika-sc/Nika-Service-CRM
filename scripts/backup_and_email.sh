#!/usr/bin/env bash
# Название: backup_and_email
# Назначение: Делает ежедневный бэкап PostgreSQL + файлов проекта и отправляет архив на email.
# За что отвечает: Архивация CRM на VPS, максимальное сжатие xz и отправка через SMTP из настроек CRM.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RECIPIENT_EMAIL="${1:-admin@example.com}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
HOSTNAME_SHORT="$(hostname -s 2>/dev/null || echo vps)"
TS="$(date +%Y%m%d_%H%M%S)"

BACKUP_DIR="$ROOT_DIR/data/database/backups/auto"
TMP_DIR="$BACKUP_DIR/tmp_$TS"
LOG_DIR="$ROOT_DIR/data/logs"
LOG_FILE="$LOG_DIR/backup_email.log"

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

require_cmd docker
require_cmd tar
require_cmd xz
require_cmd python3

log "START backup job (recipient=$RECIPIENT_EMAIL)"

# Проверка доступности docker compose
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

DB_DUMP_FILE="$TMP_DIR/postgres_${TS}.dump"
ARCHIVE_FILE="$BACKUP_DIR/crm_full_backup_${HOSTNAME_SHORT}_${TS}.tar.xz"

log "Create PostgreSQL dump -> $DB_DUMP_FILE"
docker compose exec -T postgres pg_dump -U "$PG_USER" -d "$PG_DB" -Fc > "$DB_DUMP_FILE"

log "Create compressed full archive -> $ARCHIVE_FILE"
tar -I 'xz -9e -T0' -cf "$ARCHIVE_FILE" \
  -C "$TMP_DIR" "$(basename "$DB_DUMP_FILE")" \
  -C "$ROOT_DIR" \
  --exclude='./.git' \
  --exclude='./.cursor' \
  --exclude='./data/database/backups' \
  --exclude='./data/logs' \
  --exclude='./__pycache__' \
  --exclude='./.pytest_cache' \
  --exclude='./.venv' \
  --exclude='./venv' \
  .

ARCHIVE_SIZE_HR="$(du -h "$ARCHIVE_FILE" | awk '{print $1}')"
log "Archive ready: $ARCHIVE_FILE ($ARCHIVE_SIZE_HR)"

# Берём SMTP из CRM (general_settings), fallback: переменные окружения из .env
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

# Fallback к env контейнера web (там те же переменные, что использует CRM)
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

if [[ -z "${SMTP_SERVER:-}" ]]; then SMTP_SERVER="${WEB_MAIL_SERVER:-}"; fi
if [[ -z "${SMTP_PORT:-}" ]]; then SMTP_PORT="${WEB_MAIL_PORT:-587}"; fi
if [[ -z "${SMTP_USE_TLS:-}" ]]; then SMTP_USE_TLS="${WEB_MAIL_USE_TLS:-true}"; fi
if [[ -z "${SMTP_USE_SSL:-}" ]]; then SMTP_USE_SSL="${WEB_MAIL_USE_SSL:-false}"; fi
if [[ -z "${SMTP_USERNAME:-}" ]]; then SMTP_USERNAME="${WEB_MAIL_USERNAME:-}"; fi
if [[ -z "${SMTP_PASSWORD:-}" ]]; then SMTP_PASSWORD="${WEB_MAIL_PASSWORD:-}"; fi
if [[ -z "${SMTP_SENDER:-}" ]]; then SMTP_SENDER="${WEB_MAIL_SENDER:-$SMTP_USERNAME}"; fi

if [[ -z "${SMTP_SERVER:-}" || -z "${SMTP_USERNAME:-}" || -z "${SMTP_PASSWORD:-}" || -z "${SMTP_SENDER:-}" ]]; then
  log "ERROR: SMTP не настроен (server/username/password/sender)"
  exit 3
fi

export BACKUP_EMAIL_TO="$RECIPIENT_EMAIL"
export BACKUP_ARCHIVE_PATH="$ARCHIVE_FILE"
export BACKUP_TS="$TS"
export BACKUP_HOST="$HOSTNAME_SHORT"
export BACKUP_SIZE="$ARCHIVE_SIZE_HR"
export BACKUP_ARCHIVE_BASENAME="$(basename "$ARCHIVE_FILE")"

log "Send archive via SMTP ($SMTP_SERVER:$SMTP_PORT) -> $RECIPIENT_EMAIL"
docker compose exec -T \
  -e BACKUP_EMAIL_TO \
  -e BACKUP_TS \
  -e BACKUP_HOST \
  -e BACKUP_SIZE \
  -e BACKUP_ARCHIVE_BASENAME \
  web python - <<'PY'
import os
import smtplib
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from app.services.settings_service import SettingsService

settings = SettingsService.get_general_settings() or {}
smtp_server = str(settings.get("mail_server") or os.getenv("MAIL_SERVER", "")).strip()
smtp_port = int(str(settings.get("mail_port") or os.getenv("MAIL_PORT", "587") or "587"))
smtp_user_raw = str(settings.get("mail_username") or os.getenv("MAIL_USERNAME", "")).strip()
smtp_password = str(settings.get("mail_password") or os.getenv("MAIL_PASSWORD", ""))
smtp_sender_raw = str(
    settings.get("mail_default_sender")
    or os.getenv("MAIL_DEFAULT_SENDER", "")
    or smtp_user_raw
).strip()
use_tls = str(
    settings.get("mail_use_tls")
    if settings.get("mail_use_tls") is not None
    else os.getenv("MAIL_USE_TLS", "true")
).strip().lower() in {"1", "true", "yes", "on", "t"}
use_ssl = str(
    settings.get("mail_use_ssl")
    if settings.get("mail_use_ssl") is not None
    else os.getenv("MAIL_USE_SSL", "false")
).strip().lower() in {"1", "true", "yes", "on", "t"}
email_to = os.environ["BACKUP_EMAIL_TO"].strip()
archive_basename = os.environ["BACKUP_ARCHIVE_BASENAME"].strip()
archive_path = Path("/app/database/backups/auto") / archive_basename
backup_ts = os.environ.get("BACKUP_TS", "")
backup_host = os.environ.get("BACKUP_HOST", "vps")
backup_size = os.environ.get("BACKUP_SIZE", "")

sender_name, sender_email = parseaddr(smtp_sender_raw)
smtp_sender = sender_email or smtp_sender_raw
_, smtp_user_email = parseaddr(smtp_user_raw)
smtp_user = smtp_user_email or smtp_user_raw

def _ascii_or_empty(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    try:
        v.encode("ascii")
        return v
    except UnicodeEncodeError:
        return ""

smtp_sender = _ascii_or_empty(smtp_sender)
smtp_user = _ascii_or_empty(smtp_user) or smtp_sender

if not archive_path.exists():
    raise FileNotFoundError(f"Archive not found in web container: {archive_path}")

msg = EmailMessage()
msg["Subject"] = f"[CRM Backup] {backup_host} {backup_ts}"
msg["From"] = smtp_sender
msg["To"] = email_to
msg.set_content(
    f"Автоматический бэкап CRM.\n"
    f"Сервер: {backup_host}\n"
    f"Время: {backup_ts}\n"
    f"Размер архива: {backup_size}\n"
    f"Файл: {archive_path.name}\n"
)

with archive_path.open("rb") as f:
    msg.add_attachment(
        f.read(),
        maintype="application",
        subtype="xz",
        filename=archive_path.name,
    )

if use_ssl:
    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=60) as server:
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
else:
    with smtplib.SMTP(smtp_server, smtp_port, timeout=60) as server:
        if use_tls:
            server.starttls()
        if smtp_user:
            server.login(smtp_user, smtp_password)
        server.send_message(msg)
PY

log "Email sent successfully"

log "Cleanup old auto backups (> ${RETENTION_DAYS} days)"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'crm_full_backup_*.tar.xz' -mtime +"$RETENTION_DAYS" -delete

log "DONE backup job"
