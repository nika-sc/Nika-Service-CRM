# Стартовый дамп PostgreSQL (bootstrap)

Файл **`nikacrm_public_sanitized.sql`** — очищенный дамп для быстрого локального старта: полная схема, справочники и демо-пользователи **без** реальных персональных данных клиентов.

## Что уже внутри

- Схема `public`, согласованная с миграциями PostgreSQL **001–008**:
  - `001` enable_extensions  
  - `002` fulltext_indexes  
  - `003` fix_id_defaults  
  - `004` perf_indexes  
  - `005` staff_chat  
  - `006` staff_chat_reactions  
  - `007` staff_chat_read_cursors  
  - `008` staff_chat_web_push  
- В **`schema_migrations_pg`** уже записаны версии **001 … 008**. После импорта при старте приложения (`docker compose up` / `python run.py`) **неприменённых Postgres SQL-миграций не останется** (при условии, что вы не меняли набор файлов в `app/database/migrations/postgres_versions/`).
- Справочники и демо-аккаунты для немедленной работы в интерфейсе.

## Импорт (один раз)

```bash
createdb -h localhost -p 5432 -U postgres nikacrm
psql -h localhost -p 5432 -U postgres -d nikacrm -f database/bootstrap/nikacrm_public_sanitized.sql
```

В **`.env`** (или переменных окружения):

```env
DB_DRIVER=postgres
DATABASE_URL=postgresql://postgres:ВАШ_ПАРОЛЬ@localhost:5432/nikacrm
```

Установите зависимости (`pip install -r requirements.txt`), запустите CRM — можно сразу входить под демо-пользователем.

**Windows (PowerShell), из корня репозитория:**

```powershell
psql -h localhost -p 5432 -U postgres -d nikacrm -f database/bootstrap/nikacrm_public_sanitized.sql
```

(Базу `nikacrm` создайте заранее в pgAdmin или через `createdb`.)

## Демо-доступ

| Логин   | Пароль |
|---------|--------|
| admin   | 111111 |
| manager | 111111 |
| master  | 111111 |
| viewer  | 111111 |

Смените пароли после первого входа в своей среде.

## SQLite

Этот дамп только для **PostgreSQL**. Для SQLite создайте пустой файл БД (или укажите путь), задайте `DB_DRIVER=sqlite` и прогоните миграции из `app/database/migrations/versions/` через `scripts/run_migrations.py` (см. раздел «Миграции» в корневом `README.md`).

## Продакшен

Не используйте демо-пароли на бою; ведите отдельные бекапы и политику миграций по внутренним правилам проекта.
