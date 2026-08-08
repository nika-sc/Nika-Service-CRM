# Деплой Nika CRM (Docker + PostgreSQL)

Краткая инструкция для VPS. Рабочая БД — **только PostgreSQL** (`DB_DRIVER=postgres`, `DATABASE_URL`).  
SQLite в новых сценариях не использовать.

Подробный пользовательский справочник: [USER_GUIDE.md](USER_GUIDE.md).  
Публичные страницы на демо: https://demo.nika-sc.ru/docs

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
   # для LAN без домена можно: TRUSTED_HOSTS=localhost,127.0.0.1,@private
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

## Обновление существующей установки (без потери БД)

Рекомендуемый способ на Linux (venv/systemd или Docker Compose):

```bash
cd /path/to/crm
sudo bash scripts/linux_upgrade.sh
# ветка:
#   REF=main sudo bash scripts/linux_upgrade.sh          # OSS / DEMO
#   REF=production sudo bash scripts/linux_upgrade.sh    # WORK
# из архива кода:
#   BUNDLE=/tmp/nika.tar.gz sudo bash scripts/linux_upgrade.sh
```

Скрипт:
1. полный архив в `data/database/backups/upgrade_YYYYmmdd_HHMMSS/` (`pg_dump -Fc` + `files.tar.xz` + копия `.env`);
2. обновляет код (`git merge --ff-only` или распаковка BUNDLE);
3. **не** перезаписывает `.env` и **не** заливает bootstrap SQL поверх живых данных;
4. ставит зависимости, применяет миграции (`scripts/run_migrations.py`), перезапускает сервис.

**Не** используйте `ubuntu_2404_bootstrap.sh` / `linux_setup.sh` для апгрейда — bootstrap перезаписывает `.env`.

Ручное обновление (если скрипт недоступен):

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

Два равноправных источника (приоритет у заполненных полей в CRM):

1. **Настройки → Общие → Почта (SMTP)** — основной путь для Windows Offline и большинства установок.
   При сохранении CRM обновляет `MAIL_*` в `.env` (если файл есть).
2. Переменные `MAIL_*` в `.env` — шаблон пустых ключей ставится при Linux/Windows install
   (`scripts/templates/mail.env.snippet`, `.env.example`).

```
MAIL_SERVER=smtp.mail.ru
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your@bk.ru
MAIL_PASSWORD=...
# Тот же mailbox, что логин (не noreply@example.com):
MAIL_DEFAULT_SENDER=Nika CRM <your@bk.ru>
```

**Важно:** `MAIL_DEFAULT_SENDER` / поле «От кого» должно содержать **тот же email**, что `MAIL_USERNAME`. Демо-значение `noreply@example.com` провайдеры отклоняют (`550 not local sender`). Подробно: [USER_GUIDE § 13.5](USER_GUIDE.md#135-почта-smtp) и статья блога `smtp-mail-setup`.

После ручной правки `.env` — перезапуск приложения (`docker compose up -d` / служба Windows). После сохранения в UI CRM перезапуск обычно не обязателен (процесс обновляет `os.environ`).

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
