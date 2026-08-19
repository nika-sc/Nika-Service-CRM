#!/usr/bin/env bash
# Опциональный post-install hardening для Ubuntu VPS (WORK / self-hosted OSS).
#
#   sudo bash scripts/linux_hardening.sh
#   sudo bash scripts/linux_hardening.sh --confirm-ssh-key
#   sudo bash scripts/linux_hardening.sh --install-backup-cron
#   CRM_DIR=/opt/nika-service-crm sudo bash scripts/linux_hardening.sh
#
# Не перезаписывает существующие jail/nginx конфиги целиком — только merge шаблонов.
set -euo pipefail

CONFIRM_SSH_KEY=0
INSTALL_BACKUP_CRON=0
INSTALL_MODSECURITY=0
CRM_DIR="${CRM_DIR:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --confirm-ssh-key) CONFIRM_SSH_KEY=1; shift ;;
    --install-backup-cron) INSTALL_BACKUP_CRON=1; shift ;;
    --install-modsecurity) INSTALL_MODSECURITY=1; shift ;;
    --crm-dir) CRM_DIR="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) echo "Неизвестный аргумент: $1"; exit 1 ;;
  esac
done

LOG() { echo "[linux_hardening $(date '+%H:%M:%S')] $*"; }
die() { LOG "ERROR: $*"; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "запустите от root (sudo)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
[[ -n "$CRM_DIR" ]] || CRM_DIR="$ROOT_DIR"
HARDENING_SRC="$ROOT_DIR/deploy/hardening"

export DEBIAN_FRONTEND=noninteractive

LOG "CRM_DIR=$CRM_DIR"

# --- UFW ---
if command -v ufw >/dev/null 2>&1; then
  if ufw status 2>/dev/null | grep -qi "Status: active"; then
    LOG "ufw: уже active"
  else
    ufw default deny incoming || true
    ufw default allow outgoing || true
    ufw allow 22/tcp comment 'SSH' || true
    ufw allow 80/tcp comment 'HTTP' || true
    ufw allow 443/tcp comment 'HTTPS' || true
    ufw --force enable
    LOG "ufw: enabled (22/80/443)"
  fi
else
  apt-get update -qq
  apt-get install -y -qq ufw
  ufw default deny incoming || true
  ufw default allow outgoing || true
  ufw allow 22/tcp || true
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
  ufw --force enable
  LOG "ufw: installed and enabled"
fi

# --- fail2ban ---
if ! command -v fail2ban-client >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq fail2ban
fi
mkdir -p /etc/fail2ban/filter.d /etc/fail2ban/jail.d
if [[ -f "$HARDENING_SRC/fail2ban/filter.d/nginx-nikacrm-scan.conf.example" ]]; then
  install -m 0644 -D \
    "$HARDENING_SRC/fail2ban/filter.d/nginx-nikacrm-scan.conf.example" \
    /etc/fail2ban/filter.d/nginx-nikacrm-scan.conf
fi
if [[ -f "$HARDENING_SRC/fail2ban/jail.d/nikacrm.local.example" ]]; then
  install -m 0644 -D \
    "$HARDENING_SRC/fail2ban/jail.d/nikacrm.local.example" \
    /etc/fail2ban/jail.d/nikacrm.local
fi
systemctl enable fail2ban >/dev/null 2>&1 || true
systemctl restart fail2ban || LOG "WARN: fail2ban restart failed"
LOG "fail2ban: jails nikacrm + sshd"

# --- unattended-upgrades ---
if ! dpkg -l unattended-upgrades >/dev/null 2>&1; then
  apt-get install -y -qq unattended-upgrades apt-listchanges
fi
if [[ -f /etc/apt/apt.conf.d/50unattended-upgrades ]]; then
  if ! grep -q '"${distro_id}:${distro_codename}-security"' /etc/apt/apt.conf.d/50unattended-upgrades 2>/dev/null; then
    LOG "WARN: проверьте /etc/apt/apt.conf.d/50unattended-upgrades вручную"
  fi
fi
LOG "unattended-upgrades: installed"

# --- .env permissions ---
if [[ -f "$CRM_DIR/.env" ]]; then
  chmod 600 "$CRM_DIR/.env"
  LOG ".env: chmod 600"
fi

# --- SSH hardening (opt-in) ---
if [[ "$CONFIRM_SSH_KEY" == "1" ]]; then
  if [[ ! -s /root/.ssh/authorized_keys ]]; then
    die "нет /root/.ssh/authorized_keys — не отключаем PasswordAuthentication"
  fi
  SSHD="/etc/ssh/sshd_config"
  cp -a "$SSHD" "${SSHD}.bak.$(date +%Y%m%d%H%M%S)"
  for kv in "PermitRootLogin prohibit-password" "PasswordAuthentication no" "MaxAuthTries 3"; do
    key="${kv%% *}"
    val="${kv#* }"
    if grep -qE "^[#[:space:]]*${key}\b" "$SSHD"; then
      sed -i "s/^[#[:space:]]*${key}.*/${key} ${val}/" "$SSHD"
    else
      echo "${key} ${val}" >>"$SSHD"
    fi
  done
  sshd -t
  systemctl reload sshd
  LOG "sshd: key-only (PasswordAuthentication no)"
else
  LOG "sshd: без изменений (добавьте --confirm-ssh-key после проверки входа по ключу)"
fi

# --- ModSecurity templates (opt-in install) ---
if [[ "$INSTALL_MODSECURITY" == "1" ]]; then
  apt-get install -y -qq libnginx-mod-http-modsecurity modsecurity-crs || \
    apt-get install -y -qq libmodsecurity3 libnginx-mod-http-modsecurity || \
    LOG "WARN: пакеты ModSecurity не найдены — установите вручную для вашего дистрибутива"
  mkdir -p /etc/nginx/modsecurity
  if [[ -f "$HARDENING_SRC/modsecurity/modsecurity.conf.example" ]]; then
    install -m 0644 "$HARDENING_SRC/modsecurity/modsecurity.conf.example" /etc/nginx/modsecurity/modsecurity.conf
  fi
  if [[ -f "$HARDENING_SRC/modsecurity/crs-setup.conf.example" ]]; then
    install -m 0644 "$HARDENING_SRC/modsecurity/crs-setup.conf.example" /etc/nginx/modsecurity/crs-setup.conf
  fi
  if [[ -f "$HARDENING_SRC/nginx/modsecurity-snippet.conf.example" ]]; then
    LOG "ModSecurity snippet: merge deploy/hardening/nginx/modsecurity-snippet.conf.example в host nginx server {}"
  fi
  LOG "ModSecurity: DetectionOnly config installed under /etc/nginx/modsecurity/"
fi

# --- backup cron ---
if [[ "$INSTALL_BACKUP_CRON" == "1" ]]; then
  BACKUP_SCRIPT="$CRM_DIR/scripts/backup_and_email.sh"
  [[ -x "$BACKUP_SCRIPT" ]] || chmod +x "$BACKUP_SCRIPT" 2>/dev/null || true
  CRON_LINE="30 3 * * * cd $CRM_DIR && bash scripts/backup_and_email.sh >> $CRM_DIR/data/logs/backup_cron.log 2>&1"
  (crontab -l 2>/dev/null | grep -Fv "backup_and_email.sh"; echo "$CRON_LINE") | crontab -
  LOG "cron: backup_and_email.sh ~03:30 daily"
fi

# --- Redis warning for venv multi-worker ---
if [[ -f "$CRM_DIR/.env" ]] && grep -q 'RATELIMIT_STORAGE_URI=memory://' "$CRM_DIR/.env" 2>/dev/null; then
  LOG "WARN: RATELIMIT_STORAGE_URI=memory:// — при нескольких gunicorn-воркерах lockout/rate-limit слабее; используйте Redis (Docker compose или REDIS_URL)"
fi

echo
echo "============================================================"
echo " Hardening завершён"
echo " UFW:        $(ufw status 2>/dev/null | head -1 || echo n/a)"
echo " fail2ban:   $(fail2ban-client status 2>/dev/null | grep 'Jail list' || echo n/a)"
echo " ModSecurity: ${INSTALL_MODSECURITY} (--install-modsecurity для DetectionOnly)"
echo " Документация: docs/DEPLOY.md § Production hardening"
echo "============================================================"
