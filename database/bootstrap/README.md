# Стартовый дамп PostgreSQL (bootstrap)

Файл **`nikacrm_public_sanitized.sql`** — очищенный дамп для быстрого локального старта: полная схема, справочники и демо-пользователи **без** реальных персональных данных клиентов.

## Что уже внутри

- Схема `public`, согласованная с миграциями PostgreSQL **001–024**.
- В **`schema_migrations_pg`** записаны версии **001 … 024** (все файлы из `postgres_versions/`, без пропусков). После импорта `run_migrations.py` не должен показывать pending. Скрипт `database/add_indexes.py` — наследие SQLite, для этой установки **не** нужен.
- В конце дампа — идемпотентные DDL/seed из `011`–`024` (demo visitors + счета B2B + связи каталога/`shop_sale_id` + предварительная стоимость + правка квитанции + диагностика/фото для ЛК + история диагностики + связи модели с типом/маркой + литерал `\\n` в квитанции + шаблоны диагностики + `is_active` как 0/1 + стартовые тексты + журнал писем клиенту).
- Справочники и демо-аккаунты для немедленной работы в интерфейсе.
- Актуальные печатные формы: квитанция клиенту (одна строка «Внешний вид / комплектация», предварительная стоимость), техническая форма мастера, товарный чек, акт работ, а также счёт / акт / накладная B2B.
- Права `view_invoices` / `manage_invoices` / `mark_invoice_paid` для ролей admin/manager (viewer — только просмотр).

## Как ставится база с OSS (типичные пути)

1. **Быстрый старт (рекомендуется):** импорт этого дампа в пустую БД PostgreSQL → в `.env` указать `DB_DRIVER=postgres` и `DATABASE_URL` → `pip install` → `python run.py` (или Docker / `linux_setup.sh`).
2. **Скрипт Ubuntu:** `scripts/linux_setup.sh` → `ubuntu_2404_bootstrap.sh` импортирует `nikacrm_public_sanitized.sql`, затем запускает `scripts/run_migrations.py` (если в репо появились миграции новее дампа — применятся автоматически).
3. **Docker:** при старте контейнера `docker-entrypoint.sh` вызывает `run_migrations.py`.
4. **Пустая БД без дампа:** достаточно `DATABASE_URL` — при первом запуске применятся все файлы из `app/database/migrations/postgres_versions/` (001…024 и дальше). Дамп быстрее и сразу даёт демо-логины/справочники.

После импорта актуального дампа неприменённых миграций обычно нет. Если клонировали старый снимок репо — обновите `main` и снова прогоните `run_migrations.py` / перезапустите сервис.

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
