# PostgreSQL release runbook (2026-03-30)

## 1. Release artifacts in `master`
- PostgreSQL bootstrap dump:
  - `database/backups/postgres.bootstrap_vps_sync_20260330.dump`
- SQLite source snapshot used for migration:
  - `database/backups/service_center.vps_20260330_205309.db`
- Migration and cutover scripts:
  - `app/database/postgres_migration.py`
  - `save/scripts/postgres_cutover_migration.py`
  - `save/scripts/postgres_post_cutover_checks.py`

## 2. Local bootstrap (fresh PostgreSQL)
```bash
createdb -h localhost -p 5432 -U nikacrm_local nikacrm
pg_restore -h localhost -p 5432 -U nikacrm_local -d nikacrm --clean --if-exists database/backups/postgres.bootstrap_vps_sync_20260330.dump
```

## 3. Required env for PostgreSQL
- `DB_DRIVER=postgres`
- `DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<db>`
- Optional pooling:
  - `DB_POOL_MINCONN=2`
  - `DB_POOL_MAXCONN=20`

## 4. Stage A (parallel on VPS, no prod switch)
1. В отдельном deploy-профиле поднять `postgres` контейнер.
2. Импортировать SQLite в PostgreSQL через `save/scripts/postgres_cutover_migration.py`.
3. Запустить `save/scripts/postgres_post_cutover_checks.py`.
4. Прогнать smoke по маршрутам:
   - `/all_orders`, `/clients`, `/finance/cash`, `/salary`, `/shop`.
5. Сверить row counts по таблицам: `orders`, `customers`, `payments`, `parts`.

## 5. Stage B (cutover)
1. Окно обслуживания: временно стоп записи.
2. Обновить SQLite snapshot и выполнить финальную миграцию в PostgreSQL.
3. Переключить env на PostgreSQL.
4. Перезапустить контейнеры.
5. Запустить post-checks и smoke.

## 6. Rollback readiness
- Хранить перед cutover:
  - SQLite snapshot (последний)
  - PostgreSQL dump pre-cutover
  - deploy commit/tag
- Rollback шаги:
  1. Вернуть `DB_DRIVER=sqlite` и `DATABASE_PATH=data/database/service_center.db`.
  2. Перезапустить контейнеры.
  3. При необходимости откатить код к pre-cutover commit.

## 7. Stop/Go criteria
- **Go**: post-checks без ошибок, smoke routes `200`, ключевые бизнес-сценарии проходят.
- **Stop**: расхождение row counts, критическая ошибка записи/кассы/зарплаты, неустойчивый web.
