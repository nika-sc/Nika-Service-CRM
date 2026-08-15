#!/usr/bin/env bash
# One-shot установка Nika CRM на Ubuntu 22.04 / 24.04 (аналог Windows SETUP).
#
#   sudo bash scripts/linux_setup.sh
#   sudo bash scripts/linux_setup.sh --with-nginx
#   sudo bash scripts/linux_setup.sh --harden
#   DEST=/opt/nika-crm REPO_URL=https://github.com/nika-sc/Nika-Service-CRM.git sudo bash scripts/linux_setup.sh
#   sudo bash scripts/linux_setup.sh --from-dir /path/to/already/cloned
#
# После установки: systemd unit nikacrm, демо-БД (если пустая), .env, печать URL и логинов.
# Обновление существующей установки: scripts/linux_upgrade.sh (НЕ этот скрипт).
#
set -euo pipefail

WITH_NGINX=0
WITH_LAN=0
WITH_HARDEN=0
FROM_DIR=""
REPO_URL="${REPO_URL:-https://github.com/nika-sc/Nika-Service-CRM.git}"
BRANCH="${BRANCH:-main}"
DEST="${DEST:-/root/Nika-Service-CRM}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-nginx) WITH_NGINX=1; shift ;;
    --lan) WITH_LAN=1; shift ;;
    --harden) WITH_HARDEN=1; shift ;;
    --from-dir) FROM_DIR="${2:-}"; shift 2 ;;
    --dest) DEST="${2:-}"; shift 2 ;;
    --repo) REPO_URL="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *) echo "Неизвестный аргумент: $1"; exit 1 ;;
  esac
done

LOG() { echo "[linux_setup $(date '+%H:%M:%S')] $*"; }
die() { LOG "ERROR: $*"; exit 1; }

[[ "$(id -u)" -eq 0 ]] || die "запустите от root (sudo)"

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  case "${VERSION_ID:-}" in
    22.04|24.04) ;;
    *) LOG "WARN: ожидалась Ubuntu 22.04/24.04, сейчас VERSION_ID=${VERSION_ID:-unknown}" ;;
  esac
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates

if [[ -n "$FROM_DIR" ]]; then
  [[ -f "$FROM_DIR/requirements.txt" ]] || die "--from-dir без requirements.txt"
  DEST="$(cd "$FROM_DIR" && pwd)"
  LOG "Используем существующий каталог: $DEST"
elif [[ -f "$DEST/requirements.txt" ]]; then
  LOG "Каталог уже есть: $DEST"
else
  LOG "Клонирование $REPO_URL ($BRANCH) → $DEST"
  mkdir -p "$(dirname "$DEST")"
  if [[ -d "$DEST/.git" ]]; then
    git -C "$DEST" fetch --prune origin
    git -C "$DEST" checkout "$BRANCH"
    git -C "$DEST" pull --ff-only origin "$BRANCH"
  else
    git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$DEST"
  fi
fi

[[ -f "$DEST/scripts/ubuntu_2404_bootstrap.sh" ]] || die "нет scripts/ubuntu_2404_bootstrap.sh в $DEST"
chmod +x "$DEST/scripts/ubuntu_2404_bootstrap.sh" "$DEST/scripts/linux_upgrade.sh" "$DEST/scripts/linux_hardening.sh" 2>/dev/null || true

LOG "Bootstrap (зависимости, PostgreSQL, демо-дамп если БД пустая)..."
DEST="$DEST" bash "$DEST/scripts/ubuntu_2404_bootstrap.sh"

# systemd
UNIT_SRC="$DEST/deploy/systemd/nikacrm.service.example"
UNIT_DST="/etc/systemd/system/nikacrm.service"
if [[ -f "$UNIT_SRC" ]]; then
  LOG "Установка systemd unit → $UNIT_DST"
  BIND_ADDR="127.0.0.1:5000"
  if [[ "$WITH_LAN" == "1" && "$WITH_NGINX" != "1" ]]; then
    BIND_ADDR="0.0.0.0:5000"
    LOG "LAN mode: gunicorn bind $BIND_ADDR"
  fi
  sed \
    -e "s|/root/Nika-Service-CRM|$DEST|g" \
    -e "s|--bind 127.0.0.1:5000|--bind ${BIND_ADDR}|g" \
    "$UNIT_SRC" > "$UNIT_DST"
  systemctl daemon-reload
  systemctl enable --now nikacrm
  sleep 2
  systemctl is-active --quiet nikacrm && LOG "nikacrm: active" || LOG "WARN: nikacrm не active — journalctl -u nikacrm"
else
  LOG "WARN: нет $UNIT_SRC — systemd не настроен"
fi

if [[ "$WITH_LAN" == "1" && "$WITH_NGINX" != "1" ]]; then
  if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -qi "Status: active"; then
    ufw allow 5000/tcp || LOG "WARN: не удалось открыть 5000/tcp в ufw"
    LOG "ufw: allow 5000/tcp"
  fi
fi

# optional nginx
if [[ "$WITH_NGINX" == "1" ]]; then
  apt-get install -y -qq nginx
  cat >/etc/nginx/sites-available/nikacrm <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    client_max_body_size 32m;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
  ln -sfn /etc/nginx/sites-available/nikacrm /etc/nginx/sites-enabled/nikacrm
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl enable --now nginx && systemctl reload nginx
  LOG "nginx: proxy :80 → 127.0.0.1:5000"
fi

if [[ "$WITH_HARDEN" == "1" ]]; then
  LOG "Hardening VPS (ufw, fail2ban, unattended-upgrades)..."
  CRM_DIR="$DEST" bash "$DEST/scripts/linux_hardening.sh" || LOG "WARN: linux_hardening.sh завершился с ошибкой"
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
IP="${IP:-127.0.0.1}"
if [[ "$WITH_NGINX" == "1" ]]; then
  URL="http://${IP}/"
  URL_HINT=""
elif [[ "$WITH_LAN" == "1" ]]; then
  URL="http://${IP}:5000/"
  URL_HINT="LAN включён (--lan). Смените демо-пароли, если CRM доступна из сети."
else
  URL="http://127.0.0.1:5000/"
  URL_HINT="С другого ПК порт 5000 недоступен (gunicorn на 127.0.0.1). Для LAN: переустановите с --lan или добавьте --with-nginx."
fi

echo
echo "============================================================"
echo " Nika CRM установлена"
echo " Каталог:  $DEST"
echo " .env:     $DEST/.env  (права 600)"
echo " URL:      $URL"
if [[ -n "$URL_HINT" ]]; then
  echo " Подсказка: $URL_HINT"
fi
echo " Сервис:   systemctl status nikacrm"
echo
echo " Демо-логины (после bootstrap-дампа):"
echo "   admin / 111111   (см. database/bootstrap/README.md)"
echo
echo " Обновление без потери БД:"
echo "   cd $DEST && sudo bash scripts/linux_upgrade.sh"
echo "============================================================"
