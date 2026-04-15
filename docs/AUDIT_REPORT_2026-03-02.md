# Отчёт об исправлениях после аудита — 02.03.2026

## Выполненные исправления

### 1. XSS в шаблонах печати (Важно → Исправлено)

**Файл:** `app/routes/orders.py`

**Проблема:** HTML из `customer_template_rendered`, `sales_receipt_template_rendered`, `work_act_template_rendered` выводился с `|safe` без дополнительной санитизации.

**Решение:** Добавлена финальная санитизация через `bleach.clean()` в конце `_render_print_html()` перед возвратом результата. Разрешены только безопасные теги (p, table, strong, em, img, span, div и др.), скрипты и опасные атрибуты удаляются.

---

### 2. SQL-инъекция в dashboard_service (Предложение → Исправлено)

**Файл:** `app/services/dashboard_service.py`

**Проблема:** В `_has_column(cur, table, column)` имена таблиц и колонок подставлялись в PRAGMA без проверки.

**Решение:** Добавлена валидация через regex `^[a-zA-Z_][a-zA-Z0-9_]*$`. При невалидном имени возвращается `False`, запрос к БД не выполняется.

---

### 3. Bare except в order_service (Предложение → Исправлено)

**Файл:** `app/services/order_service.py`

**Проблема:** Использование `except:` без указания типа исключения.

**Решение:** Заменено на `except Exception as e:` с логированием: `logger.debug("get current_user for action log: %s", e)`.

---

### 4. clients.html — $('<div>').html(data) (Предложение → Проверено)

**Файл:** `templates/clients.html`

**Проверка:** API `/api/datatables/clients` формирует HTML на сервере с `_html.escape()` для имени, телефона, email и даты. Числовые поля — целые числа. Риск XSS отсутствует, изменений не требуется.

---

## Итоговая сводка

| № | Проблема | Статус |
|---|----------|--------|
| 1 | XSS в шаблонах печати | Исправлено |
| 2 | SQL в dashboard_service | Исправлено |
| 3 | Bare except в order_service | Исправлено |
| 4 | clients.html data escaping | Проверено, OK |

---

## Оставшиеся пункты (информационно)

- **config.py** — SECRET_KEY: проверка в `create_app` сохранена
- **Миграции** — f-string с именами таблиц: риск низкий, используются константы
- **all_services\|tojson\|safe** — данные из справочника услуг, источник доверенный
- **order_detail.css** — избыточный `!important` и закомментированный код: можно оптимизировать позже
