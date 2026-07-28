# Стартовый дамп PostgreSQL (bootstrap)

Файл **`nikacrm_public_sanitized.sql`** — очищенный дамп для быстрого локального старта: полная схема, справочники и демо-пользователи **без** реальных персональных данных клиентов.

## Что уже внутри

- Схема `public`, согласованная с миграциями PostgreSQL **001–013**.
- В **`schema_migrations_pg`** записаны версии **001 … 013**; в конце дампа — идемпотентные DDL/seed из `011`–`013` (demo visitors + счета B2B).
- Справочники и демо-аккаунты для немедленной работы в интерфейсе.
- Актуальные печатные формы: квитанция клиенту, техническая форма мастера, товарный чек, акт работ, а также счёт / акт / накладная B2B.

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

## Продакшен

Не используйте демо-пароли на бою; ведите отдельные бекапы и политику миграций по внутренним правилам проекта.
