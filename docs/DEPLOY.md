# Деплой Nika CRM (Docker + PostgreSQL)

Краткая инструкция для VPS. Рабочая БД — **только PostgreSQL** (`DB_DRIVER=postgres`, `DATABASE_URL`).  
SQLite в новых сценариях не использовать.

Подробный пользовательский справочник: [USER_GUIDE.md](USER_GUIDE.md).  
Политика OSS и порядок релиза: [OSS_RELEASE_WORKFLOW.md](OSS_RELEASE_WORKFLOW.md).

## Что должно быть в репозитории

- `docker/Dockerfile`, `docker/docker-compose.yml` (подключение из корня через `docker-compose.yml`)
- `wsgi.py`, `nginx/nginx.conf`
- `.env.example` / `docker/env.example`
- `deploy.sh` (если используете скрипт деплоя)

См. также [`docker/README.md`](../docker/README.md) и корневой [README.md](../README.md) (разделы Docker и Ubuntu 24.04).

## Требования к серверу

- Ubuntu **24.04** LTS (или совместимый)
- Docker + Docker Compose plugin
- Git
- Открытые порты HTTP/HTTPS (и SSH)

## Первый запуск

1. Клонировать нужный репозиторий и ветку:
   - рабочий (приватный): ветка `production`;
   - демо/OSS: публичный репо, ветка `main`.

2. Создать `.env` из примера:

   ```bash
   cp docker/env.example .env
   # задайте SECRET_KEY, пароли Postgres, при необходимости SMTP и TRUSTED_HOSTS
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. Запуск:

   ```bash
   chmod +x deploy.sh   # если есть
   ./deploy.sh
   # или:
   docker compose build
   docker compose up -d
   ```

4. Проверка:

   ```bash
   docker compose ps
   docker compose logs -f web
   ```

Приложение: `http://IP_СЕРВЕРА` (или домен за nginx/Caddy).

Миграции Postgres обычно применяются при старте контейнера (`docker-entrypoint` / `run_migrations.py`).

## Обновление кода

На WORK (ветка `production`):

```bash
cd /root/nikanewcrm   # путь может отличаться
git pull --ff-only origin production
docker compose build
docker compose up -d
docker compose ps
```

На DEMO (публичный `main`):

```bash
cd /root/Nika-Service-CRM
git pull --ff-only origin main
# перезапуск по принятому на сервере способу, например:
systemctl restart nikacrm
systemctl is-active nikacrm nginx
```

## Почта (опционально)

В `.env` на сервере (пароль **не** коммитить):

```
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your@email.com
MAIL_PASSWORD=...
MAIL_DEFAULT_SENDER=your@email.com
```

После правки — `docker compose up -d`.

## Web Push (чат сотрудников, опционально)

1. Сайт по **HTTPS** (требование браузеров, кроме localhost).  
2. VAPID-ключи в `.env`: `scripts/generate_staff_chat_vapid_keys.py` / `ensure_staff_chat_vapid_env.py`.  
3. Пакет `pywebpush` в окружении.  
4. Миграции с таблицей подписок Push уже в цепочке Postgres.  
5. Перезапуск приложения.

Для пользователей: [USER_GUIDE.md — чат](USER_GUIDE.md#14-чат-сотрудников).

## HTTPS

Nginx + Certbot или Caddy вместо nginx — по вашей схеме. Пример конфигов смотрите в `nginx/` и `docker/`.

## Резервное копирование (PostgreSQL)

Используйте `pg_dump` / `pg_restore` (major-версия клиента = major сервера).  
Артефакты с ПДн **не** класть в git; хранить вне репозитория.

Пример логического дампа:

```bash
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > backup_$(date +%Y%m%d).dump
```

Локальные скрипты экспорта (если есть в приватном репо) — в `scripts/`; на DEMO/OSS сверяйтесь с публичным набором файлов.
