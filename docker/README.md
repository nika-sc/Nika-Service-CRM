# Docker: NikaNewCrm

Канонические файлы: `Dockerfile`, `docker-entrypoint.sh`, `docker-compose.yml` в этой папке.

## Запуск из корня репозитория

```bash
cp docker/env.example .env
# отредактируйте .env (SECRET_KEY и пароли Postgres)

docker compose up -d
```

Корневой `docker-compose.yml` подключает этот файл через `include`, команды выполняются как раньше из корня проекта.

## Явный путь к compose

```bash
docker compose -f docker/docker-compose.yml up -d
```

Убедитесь, что `.env` лежит в корне репозитория (Compose подхватит его из текущей директории при запуске из корня).

## URL

- Через nginx: `http://localhost:8080`
- Прямо на приложение (без публикации порта в этом compose): только внутри сети compose; для отладки временно добавьте `ports: - "5000:5000"` у сервиса `web`.

## Демо-данные PostgreSQL

Импорт дампа в контейнер (из корня репозитория):

```bash
docker compose exec -T postgres psql -U nikacrm -d nikacrm < database/bootstrap/nikacrm_public_sanitized.sql
```

(подставьте пользователя/БД из вашего `.env`.)

## Обновление

```bash
git pull
docker compose build web
docker compose up -d
```
