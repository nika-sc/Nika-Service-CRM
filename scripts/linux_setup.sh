#!/usr/bin/env bash
# One-shot установка Nika CRM на Ubuntu 22.04 / 24.04 (аналог Windows SETUP).
#
#   sudo bash scripts/linux_setup.sh
#   sudo bash scripts/linux_setup.sh --with-nginx
#   DEST=/opt/nika-crm REPO_URL=https://github.com/nika-sc/Nika-Service-CRM.git sudo bash scripts/linux_setup.sh
#   sudo bash scripts/linux_setup.sh --from-dir /path/to/already/cloned
#
# После установки: systemd unit nikacrm, демо-БД (если пустая), .env, печать URL и логинов.
# Обновление существующей установки: scripts/linux_upgrade.sh (НЕ этот скрипт).
#
set -euo pipefail

WITH_NGINX=0
FROM_DIR=""
REPO_URL="${REPO_URL:-https://github.com/nika-sc/Nika-Service-CRM.git}"
BRANCH="${BRANCH:-main}"
DEST="${DEST:-/root/Nika-Service-CRM}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-nginx) WITH_NGINX=1; shift ;;
    --from-dir) FROM_DIR="${2:-}"; shift 2 ;;
    --dest) DEST="${2:-}"; shift 2 ;;
    --repo) REPO_URL="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "$0"
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
chmod +x "$DEST/scripts/ubuntu_2404_bootstrap.sh" "$DEST/scripts/linux_upgrade.sh" 2>/dev/null || true

LOG "Bootstrap (зависимости, PostgreSQL, демо-дамп если БД пустая)..."
DEST="$DEST" bash "$DEST/scripts/ubuntu_2404_bootstrap.sh"

# systemd
UNIT_SRC="$DEST/deploy/systemd/nikacrm.service.example"
UNIT_DST="/etc/systemd/system/nikacrm.service"
if [[ -f "$UNIT_SRC" ]]; then
  LOG "Установка systemd unit → $UNIT_DST"
  sed \
    -e "s|/root/Nika-Service-CRM|$DEST|g" \
    "$UNIT_SRC" > "$UNIT_DST"
  systemctl daemon-reload
  systemctl enable --now nikacrm
  sleep 2
  systemctl is-active --quiet nikacrm && LOG "nikacrm: active" || LOG "WARN: nikacrm не active — journalctl -u nikacrm"
else
  LOG "WARN: нет $UNIT_SRC — systemd не настроен"
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

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
IP="${IP:-127.0.0.1}"
if [[ "$WITH_NGINX" == "1" ]]; then
  URL="http://${IP}/"
else
  URL="http://${IP}:5000/"
fi

echo
echo "============================================================"
echo " Nika CRM установлена"
echo " Каталог:  $DEST"
echo " .env:     $DEST/.env  (права 600)"
echo " URL:      $URL"
echo " Сервис:   systemctl status nikacrm"
echo
echo " Демо-логины (после bootstrap-дампа):"
echo "   admin / 111111   (см. database/bootstrap/README.md)"
echo
echo " Обновление без потери БД:"
echo "   cd $DEST && sudo bash scripts/linux_upgrade.sh"
echo "============================================================"
