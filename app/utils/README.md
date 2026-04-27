# Utils (Утилиты)

Пакет `app.utils` содержит общие утилиты, которые используются во всех слоях приложения (routes/services/models/queries).

## Что здесь находится

- **`datetime_utils.py`**: единая работа с датой/временем с учетом `general_settings.timezone_offset` (по умолчанию Москва UTC+3).
- **`report_period.py`**: нормализация периода отчетов (параметры `preset`, `date_from`, `date_to`).
- **`validators.py` / `api_validators.py`**: валидация входных данных (телефон, email, цены и т.д.).
- **`exceptions.py`**: типовые исключения (`ValidationError`, `NotFoundError`, `DatabaseError`).
- **`error_handlers.py` / `db_error_translator.py`**: единая обработка ошибок и перевод ошибок БД в понятные сообщения.
- **`cache.py` / `cache_helpers.py`**: in-memory кэш и хелперы.
- **`pagination.py`**: пагинация для списков (используется в отчетах/таблицах).
- **`performance_monitor.py`**: измерение длительности операций/запросов (логирование slow operations).
- **`types.py`**: типы/алиасы для словарей и DTO.

## Время и timezone_offset (важно)

Для записи времени в БД и отображения в интерфейсе используйте функции из `app.utils.datetime_utils`:

- `get_moscow_now_str()` — строка времени в настроенном часовом поясе (Москва/`timezone_offset`)
- `get_moscow_now_naive()` — naive datetime (для случаев, где нужен `datetime`, но фактически время «в Москве»)

Не используйте напрямую `datetime.now()`/`CURRENT_TIMESTAMP` для записей в БД в скриптах/сервисах — это может дать расхождения с `timezone_offset`.

## Периоды отчетов

Для страниц отчётов и дашбордов используйте `normalize_date_range()`:

- если указана только одна граница — она дублируется во вторую
- если границы не указаны — применяется дефолт (`today`/`current_month`), если это нужно

