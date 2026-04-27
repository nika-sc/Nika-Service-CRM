# Углублённая проверка XSS и SQL-инъекций — 02.03.2026

## 1. XSS (Cross-Site Scripting)

### 1.1 Критично: вставка без экранирования в innerHTML

#### [Файл: templates/shop/index.html]

**Строки 643–648, 919–929**

**Проблема:** Данные из API вставляются в `innerHTML` без `escapeHtml`:

- **displaySearchResults:** `item.label` — название услуги/товара из БД. Если в названии есть `<script>`, `<img onerror=...>`, будет выполнен XSS.
- **displayCustomerResults:** `customer.name`, `customer.phone` — данные клиента. Риск, если имя/телефон содержат HTML.

**Рекомендация:** Экранировать все пользовательские поля:
- `item.label` → `escapeHtml(item.label)`
- `customer.name` → `escapeHtml(customer.name)`
- `customer.phone` → `escapeHtml(customer.phone)`

Добавить функцию `escapeHtml` (по аналогии с `static/js/search.js`) и использовать её во всех местах вставки в HTML.

---

#### [Файл: templates/salary/index.html]

**Строки 627, 679, 774, 835**

**Проблема:**

- **debtsList.innerHTML:** `item.employee_name` — имя сотрудника из API, вставляется без экранирования.
- **container.innerHTML (cards):** `emp.employee_name` — то же самое.

**Рекомендация:** Оборачивать все текстовые поля в `escapeHtml()`:
- `item.employee_name` → `escapeHtml(item.employee_name || 'Неизвестно')`
- `emp.employee_name` → `escapeHtml(emp.employee_name || 'Неизвестно')`

---

### 1.2 Использование |safe (уже защищено или контролируется)

| Файл | Контекст | Статус |
|------|----------|--------|
| `templates/order_detail.html` | `customer_template_rendered\|safe`, `sales_receipt_template_rendered\|safe`, `work_act_template_rendered\|safe` | Защищено — санитизация через bleach в `_render_print_html` |
| `templates/order_detail.html` | `all_services\|tojson\|safe` | Низкий риск — справочник услуг, `tojson` экранирует |
| `templates/warehouse/part_form.html` | `(indent ~ ...)\|safe` | `\|safe` только для indent; `node.name` экранируется отдельно |
| `templates/action_logs.html` | `value\|tojson` | Безопасно — `tojson` экранирует для JSON |
| `templates/dashboard.html`, `reports/dashboard.html` | `revenue_chart\|tojson`, `orders_chart\|tojson` | Данные чартов, контролируемый источник |
| `templates/settings.html` | `payment_method_settings.custom_methods\|tojson` | JSON в `value`, экранирование есть |

---

### 1.3 $('<div>').html(data) и аналоги

| Файл | Контекст | Статус |
|------|----------|--------|
| `templates/clients.html` | DataTables `data-order-num-pre`, `data-order-date-pre` | Данные из `/api/datatables/clients`, на сервере используется `_html.escape()` |
| `static/js/search.js` | `autocomplete.innerHTML` | Используется `escapeHtml()` для `item.text`, `item.id` |

---

### 1.4 document.write

| Файл | Контекст | Статус |
|------|----------|--------|
| `templates/order_detail.html` | `w.document.write(...)` при печати | `html` берётся из DOM текущей страницы, контент уже прошёл санитизацию |

---

### 1.5 innerHTML с фиксированным текстом

Использование `innerHTML` для статического контента (сообщения, спиннеры, пустые состояния) считается допустимым — там нет пользовательских данных. Примеры: `static/js/notifications.js`, `templates/reports/dashboard.html` (пустые состояния).

---

## 2. SQL-инъекции

### 2.1 Проверенные файлы

#### Безопасно (параметризация / контролируемые условия)

| Файл | Контекст | Причина |
|------|----------|---------|
| `app/routes/shop.py` | `api_search`, `api_search_customers` | Параметры передаются во второй аргумент `execute()`, структура SQL задана константами |
| `app/services/reports_service.py` | f-string с `where_sql`, `shop_sales_where_sql` | Условия собираются из фиксированных строк, значения — в `params` |
| `app/database/queries/comment_queries.py` | `IN ({placeholders})` | `placeholders` = `','.join('?' * len(order_ids))`, значения в `order_ids` |
| `app/database/queries/warehouse_queries.py` | f-string | `where_sql` строится из константных условий, значения — в `params` |
| `app/services/customer_service.py` | f-string | Структура WHERE фиксирована, значения в `params` |
| `app/database/queries/order_queries.py` | f-string | `not_deleted_clause` — константа, `order_id` в params |
| `app/services/reference_service.py` | f-string | Переменные — из схемы БД, не из запроса пользователя |
| `app/services/finance_service.py` | f-string | Структура запросов задана кодом, параметры в `params` |
| `app/database/queries/salary_queries.py` | f-string | Аналогично — структура и параметры разделены |
| `app/services/template_service.py` | `SET {', '.join(updates)}` | Список полей ограничен (`name`, `description`, `template_data`, `is_public`) |
| `app/database/queries/reference_queries.py` | `{parts_price_col}` | `parts_price_col` — `retail_price` или `price` по схеме |
| `app/database/queries/payment_queries.py` | f-string | Структура фиксирована |

---

#### С защитой

| Файл | Контекст | Реализовано |
|------|----------|-------------|
| `app/database/audit.py` | PRAGMA с `{table_name}`, `{index_name}` | Валидация `_validate_sqlite_identifier()` |
| `app/services/dashboard_service.py` | PRAGMA с `{table}` | Валидация regex в `_has_column()` |

---

#### Миграции (низкий риск)

| Файл | Контекст | Причина |
|------|----------|---------|
| `app/database/migrations/versions/*` | `PRAGMA table_info({table})`, `DROP TABLE`, `ALTER TABLE` | `table`, `col_name`, `index_name` берутся из констант и списков в коде |
| `027_payments_receipts_standardize.py` | `ADD COLUMN {col} {ddl}` | `col`, `ddl` из списка `payments_new_cols` |
| `050_general_settings_automation_links.py` | `ADD COLUMN {col_name} {col_def}` | Из списка `additions` |
| `051_director_email_notifications.py` | То же | Из списка `additions` |
| `042_performance_indexes.py` | `CREATE INDEX`, `DROP INDEX` | Имена и столбцы из списка `indexes` |

---

### 2.2 Источники пользовательского ввода

Проверены точки входа:

- `request.form.get`, `request.args.get`, `request.json`
- Маршруты: `orders`, `customers`, `shop`, `main`, `customer_portal`, `reports`, `finance`, `warehouse`, `api`, `search` и др.

Во всех разобранных SQL-запросах пользовательский ввод передаётся только через параметры (второй аргумент `execute()`), а не через подстановку в строку запроса.

---

## 3. Резюме

### XSS — нужно исправить

1. **templates/shop/index.html**  
   Экранировать `item.label`, `customer.name`, `customer.phone` при вставке в `innerHTML`.

2. **templates/salary/index.html**  
   Экранировать `item.employee_name` и `emp.employee_name` при вставке в `innerHTML`.

### SQL-инъекции

- Обнаруженные уязвимости закрыты (`audit.py`, `dashboard_service.py`).
- Остальные SQL-запросы используют параметризацию или жёстко заданные имена объектов.
