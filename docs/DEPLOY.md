# NikaNewCrm — Ручной деплой (вариант A)

## Подготовка

### 1. Ветка production

```bash
git checkout -b production
git push -u origin production
```

### 2. Файлы для деплоя

Убедитесь, что в репозитории есть:

- `Dockerfile`
- `docker-compose.yml`
- `wsgi.py`
- `nginx/nginx.conf`
- `.env.example`
- `deploy.sh`

---

## Первый запуск на VPS

### Требования

- Ubuntu 22.04 (или аналог)
- Docker и Docker Compose
- Git (если клонируете репозиторий на сервер)

### Установка Docker (если ещё нет)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Перелогиньтесь или: newgrp docker
```

### Шаги

1. **Клонирование репозитория** (или копирование файлов)

   ```bash
   git clone <url-репозитория> nikanewcrm
   cd nikanewcrm
   git checkout production
   ```

2. **Создание .env**

   ```bash
   cp .env.example .env
   nano .env   # Заполните SECRET_KEY и при необходимости остальное
   ```

   Для отправки писем (клиентам и директору) добавьте в `.env` на сервере (не коммитить пароль в репозиторий):

   ```
   MAIL_SERVER=smtp.example.com
   MAIL_PORT=587
   MAIL_USERNAME=your@email.com
   MAIL_PASSWORD=ваш_пароль_или_пароль_приложения
   MAIL_DEFAULT_SENDER=your@email.com
   ```

   После изменения `.env` перезапустите контейнер: `docker compose up -d`.

   Сгенерировать `SECRET_KEY`:

   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **Запуск**

   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

4. **Проверка**

   ```bash
   docker compose ps
   docker compose logs -f web
   ```

   Приложение доступно по `http://IP_СЕРВЕРА`.

---

## Обновление (после merge в production)

1. На VPS:

   ```bash
   cd nikanewcrm
   ./deploy.sh
   ```

2. Или вручную:

   ```bash
   git pull origin production
   docker compose build
   docker compose up -d
   ```

---

## Web Push (чат сотрудников, опционально)

Чтобы кнопка **📡** в чате работала на проде:

1. Убедитесь, что сайт открыт по **HTTPS** (требование браузеров для Push, кроме localhost).
2. В `.env` на сервере задайте ключи VAPID (не коммитить приватный ключ):
   - сгенерировать локально: `python scripts/generate_staff_chat_vapid_keys.py`;
   - или одноразово дописать в `.env`: `python scripts/ensure_staff_chat_vapid_env.py` (только на доверенной машине).
3. В образе/на хосте после обновления кода: `pip install -r requirements.txt` (нужен пакет **pywebpush**).
4. Примените миграции БД: **061** (SQLite) / **008** Postgres — таблица `staff_chat_web_push_subscriptions` (обычно при старте контейнера, см. `docker-entrypoint.sh` / `run_migrations.py`).
5. Перезапустите приложение.

Подробности для пользователей: [USER_GUIDE.md](USER_GUIDE.md#чат-сотрудников). API: [API.md](API.md).

## HTTPS (Let's Encrypt)

Для SSL можно использовать Caddy или Certbot с nginx.

### Вариант: Caddy вместо nginx

В `docker-compose.yml` заменить сервис nginx на Caddy — он сам получает сертификаты. Либо настроить nginx + certbot по отдельной инструкции.

---

## Перенос существующей базы данных

Если у вас уже есть `service_center.db` с локальной разработки:

1. Скопируйте файл на VPS в `data/database/service_center.db`
2. Миграции применятся автоматически при первом `docker compose up`

## Резервное копирование

**Архивация на S3 (s3.hoztnode.net):** ISPmanager Autobackup отправляет на удалённый сервер:
- вся папка CRM (`/root/nikanewcrm`) — код, конфиги, `data/database/` (БД и папка `backups/`);
- ежедневные копии БД (`/root/backups/db_YYYYMMDD.db`).

Расписание на VPS:
- **01:45** — копирование БД в `/root/backups/db_YYYYMMDD.db`;
- **01:56** — запуск Autobackup (упаковка и выгрузка на S3).

Конфиг: `/opt/autobackup/config.yml` (в `backup_paths` добавлены `/root/backups` и `/root/nikanewcrm`).

Ручной запуск полного бэкапа на S3:
```bash
ssh root@VPS "cd /opt/autobackup && ./backup"
```

Локальный быстрый бэкап БД:
```bash
cp data/database/service_center.db backup_$(date +%Y%m%d).db
```
