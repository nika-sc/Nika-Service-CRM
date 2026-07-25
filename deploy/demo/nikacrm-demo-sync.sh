#!/usr/bin/env bash
# Синхронизация демо-CRM с публичным репозиторием (ветка main).
# Установка: см. deploy/demo/README.md
set -euo pipefail

if [[ -f /etc/default/nikacrm-demo-sync ]]; then
  # shellcheck source=/dev/null
  . /etc/default/nikacrm-demo-sync
fi

: "${DEMO_ROOT:=/root/Nika-Service-CRM}"
: "${DEMO_BRANCH:=main}"
: "${DEMO_REMOTE:=origin}"
: "${DEMO_SERVICE:=nikacrm}"

MODE="${1:-poll}"
cd "$DEMO_ROOT"
export GIT_TERMINAL_PROMPT=0

log() { echo "[nikacrm-demo-sync] $*"; }

run_pip() {
  if [[ -x "${DEMO_ROOT}/venv/bin/pip" ]]; then
    "${DEMO_ROOT}/venv/bin/pip" install -q -r "${DEMO_ROOT}/requirements.txt"
  else
    log "venv/bin/pip не найден — пропуск pip install"
  fi
}

# nginx отдаёт /static из DEMO_ROOT; каталог не должен быть 750 (www-data потеряет доступ).
fix_static_perms() {
  if [[ -x /usr/local/sbin/nikacrm-fix-static-perms.sh ]]; then
    /usr/local/sbin/nikacrm-fix-static-perms.sh || log "fix-static-perms завершился с ошибкой"
    return 0
  fi
  if id nikacrm >/dev/null 2>&1; then
    chown -R nikacrm:nikacrm "$DEMO_ROOT" || true
  fi
  chmod 755 "$DEMO_ROOT" || true
  if [[ -d "${DEMO_ROOT}/static" ]]; then
    find "${DEMO_ROOT}/static" -type d -exec chmod 755 {} \;
    find "${DEMO_ROOT}/static" -type f -exec chmod 644 {} \;
  fi
  chmod 640 "${DEMO_ROOT}/.env" 2>/dev/null || true
}

case "$MODE" in
  boot)
    git fetch "$DEMO_REMOTE" "$DEMO_BRANCH" || { log "fetch не удался, стартуем с текущим кодом"; exit 0; }
    git merge --ff-only "${DEMO_REMOTE}/${DEMO_BRANCH}" || { log "ff-only merge не удался (локальные отличия?) — стартуем с текущим кодом"; exit 0; }
    run_pip || log "pip install завершился с ошибкой, продолжаем"
    fix_static_perms
    ;;
  poll)
    git fetch "$DEMO_REMOTE" "$DEMO_BRANCH" || { log "fetch не удался, пропуск цикла"; exit 0; }
    local_rev=$(git rev-parse HEAD)
    remote_rev=$(git rev-parse "${DEMO_REMOTE}/${DEMO_BRANCH}")
    if [[ "$local_rev" == "$remote_rev" ]]; then
      log "уже актуально $(git rev-parse --short HEAD)"
      exit 0
    fi
    git merge --ff-only "${DEMO_REMOTE}/${DEMO_BRANCH}"
    run_pip
    fix_static_perms
    systemctl restart "$DEMO_SERVICE"
    log "обновлено до $(git rev-parse --short HEAD), перезапущен ${DEMO_SERVICE}"
    ;;
  *)
    echo "Использование: $0 boot|poll" >&2
    exit 1
    ;;
esac
