#!/usr/bin/env bash
# Название: backup_and_email
# Назначение: Ежедневный бэкап данных CRM (dump + .env + uploads + nginx/LE), без исходников git.
# Режимы: Docker Compose или host Postgres + systemd (self-hosted).
# Получатель: argv $1, иначе BACKUP_EMAIL_TO, иначе MAIL_USERNAME из .env.
# Не зашивать личную почту и IP сервера — скрипт уходит в публичный OSS.

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

DB_DUMP_FILE="$TMP_DIR/postgres_${TS}.dump"
ARCHIVE_FILE="$BACKUP_DIR/crm_data_backup_${HOSTNAME_SHORT}_${TS}.tar.xz"

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
  require_cmd pg_dump
  require_cmd psql
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

# Данные для восстановления, не исходники с GitHub (docs/static/vendor раздувают письмо).
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

{
  echo "label=$SITE_LABEL"
  echo "created=$(date -Is)"
  echo "host=$(hostname -f 2>/dev/null || hostname)"
  echo "mode=$MODE"
  echo "purpose=restore data only; code from git (GIT_HEAD / GIT_REMOTE)"
  echo "contents=postgres dump, .env, data/uploads, nginx, letsencrypt, monitoring"
} > "$STAGE/MANIFEST.txt"

log "Create compressed data archive -> $ARCHIVE_FILE"
if [[ -z "${BACKUP_XZ_OPTS:-}" ]]; then
  mem_mb="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
  if [[ "$mem_mb" -gt 0 && "$mem_mb" -lt 2048 ]]; then
    BACKUP_XZ_OPTS="-6 -T1"
    log "Low memory (${mem_mb}MiB): using xz $BACKUP_XZ_OPTS"
  else
    BACKUP_XZ_OPTS="-9e -T0"
  fi
fi
tar -I "xz $BACKUP_XZ_OPTS" -cf "$ARCHIVE_FILE" -C "$TMP_DIR" payload

if [[ -z "${BACKUP_ARCHIVE_PASSWORD:-}" ]]; then
  log "ERROR: BACKUP_ARCHIVE_PASSWORD пуст в .env — открытый дамп на почту не шлём"
  rm -f "$ARCHIVE_FILE"
  exit 2
fi
SEVENZ_FILE="${ARCHIVE_FILE%.tar.xz}.7z"
log "7z AES-256 + encrypt headers -> $SEVENZ_FILE"
rm -f "$SEVENZ_FILE"
set +e
(
  cd "$(dirname "$ARCHIVE_FILE")" || exit 2
  "$SEVENZ_BIN" a -t7z -mx=0 -mhe=on -y \
    "-p${BACKUP_ARCHIVE_PASSWORD}" "$SEVENZ_FILE" "$(basename "$ARCHIVE_FILE")" >/dev/null
)
rc=$?
set -e
if [[ $rc -gt 1 || ! -f "$SEVENZ_FILE" ]]; then
  log "ERROR: 7z failed (rc=$rc)"
  exit 2
fi
rm -f "$ARCHIVE_FILE"
ARCHIVE_FILE="$SEVENZ_FILE"

ARCHIVE_SIZE_HR="$(du -h "$ARCHIVE_FILE" | awk '{print $1}')"
log "Archive ready: $ARCHIVE_FILE ($ARCHIVE_SIZE_HR)"

if [[ "${BACKUP_PUSH_PRIVATE:-}" == "1" ]]; then
  log "Push encrypted snapshot to private branch work-restore"
  if ! bash "$ROOT_DIR/scripts/backup_push_work_restore.sh" "$ARCHIVE_FILE"; then
    log "WARN: private git snapshot push failed (disk archive still kept)"
  fi
fi

if [[ "${BACKUP_SKIP_EMAIL:-}" == "1" ]]; then
  log "BACKUP_SKIP_EMAIL=1 — archive kept, no mail"
  exit 0
fi

export BACKUP_EMAIL_TO="$RECIPIENT_EMAIL"
export BACKUP_ARCHIVE_PATH="$ARCHIVE_FILE"
export BACKUP_TS="$TS"
export BACKUP_HOST="$HOSTNAME_SHORT"
export BACKUP_SIZE="$ARCHIVE_SIZE_HR"
export BACKUP_SITE_LABEL="$SITE_LABEL"
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

# Envelope / AUTH — только ASCII mailbox; display name с кириллицей нельзя в login
smtp_sender = _ascii_or_empty(smtp_sender) or _ascii_or_empty(smtp_user)
smtp_user = _ascii_or_empty(smtp_user) or smtp_sender
# Пароль SMTP обязан быть ASCII (smtplib AUTH PLAIN)
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
site_label = os.environ.get("BACKUP_SITE_LABEL") or f"CRM {backup_host}"
msg["Subject"] = f"[CRM Backup] {site_label} {backup_ts}"
msg["From"] = smtp_sender
msg["To"] = email_to
msg.set_content(
    f"Автоматический бэкап данных CRM (без исходников с GitHub).\n"
    f"Сайт: {site_label}\n"
    f"Сервер: {backup_host}\n"
    f"Время: {backup_ts}\n"
    f"Размер архива: {backup_size}\n"
    f"Файл: {archive_path.name}\n\n"
    f"В архиве: PostgreSQL dump, .env, загрузки (фото диагностики и т.п.),\n"
    f"nginx и Let's Encrypt (если есть на хосте).\n"
    f"Код приложения — из git (см. GIT_HEAD в архиве).\n"
    f"Файл: 7z AES-256, имена внутри тоже зашифрованы.\n"
    f"Пароль в письме нет: BACKUP_ARCHIVE_PASSWORD в .env на сервере.\n"
    f"Откройте в 7-Zip и введите пароль. Внутри будет tar.xz с payload/.\n"
)

# Крупные вложения многие SMTP режут — шлём без файла, путь на диске
attach_max = int(os.environ.get("BACKUP_ATTACH_MAX_BYTES") or "28000000")
size_bytes = archive_path.stat().st_size
if size_bytes <= attach_max:
    with archive_path.open("rb") as f:
        att_subtype = "x-7z-compressed" if archive_path.name.endswith(".7z") else "octet-stream"
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype=att_subtype,
            filename=archive_path.name,
        )
else:
    msg.set_content(
        msg.get_content()
        + f"\nВложение НЕ приложено (размер {size_bytes} > {attach_max}).\n"
        + f"Файл на сервере: {archive_path}\n"
        + f"scp root@{backup_host}:{archive_path} .\n"
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
      -e BACKUP_SITE_LABEL \
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
    att_subtype = "x-7z-compressed" if archive_path.name.endswith(".7z") else "octet-stream"
    msg.add_attachment(f.read(), maintype="application", subtype=att_subtype, filename=archive_path.name)
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
find "$BACKUP_DIR" -maxdepth 1 -type f \( \
  -name 'crm_full_backup_*.tar.xz' -o -name 'crm_full_backup_*.tar.xz.enc' \
  -o -name 'crm_data_backup_*.tar.xz' -o -name 'crm_data_backup_*.tar.xz.enc' \
  -o -name 'crm_data_backup_*.7z' \
\) -mtime +"$RETENTION_DAYS" -delete

log "DONE backup job"
