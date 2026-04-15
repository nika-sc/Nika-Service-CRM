#!/bin/bash
# NikaNewCrm — ручной деплой на VPS
# Запускать на сервере в каталоге проекта: ./deploy.sh

set -e

echo "=== NikaNewCrm deploy ==="

# Директории для данных
mkdir -p data/database data/logs

# Обновление кода (если используется git на сервере)
if [ -d .git ]; then
    echo "Git pull..."
    git pull origin production 2>/dev/null || git pull 2>/dev/null || true
fi

# Сборка и запуск
echo "Docker build..."
docker compose build --no-cache

echo "Docker up..."
docker compose up -d

echo "=== Готово. Проверьте: docker compose ps ==="
