# API Документация

Документация всех API endpoints системы Nika CRM.

**Версия:** 2.3  
**Последнее обновление:** 2026-03-12

## Базовый URL

```
http://127.0.0.1:5000
```

## Аутентификация

**Все API endpoints требуют аутентификации** через Flask-Login. Для доступа необходимо:

1. Войти в систему через `/login`
2. Получить сессионную cookie
3. Использовать cookie в последующих запросах

**Важно:** Все 61 API endpoint защищены `@login_required`. Доступ без авторизации блокируется (302, 401, 403).

## Безопасность

- ✅ Все endpoints защищены аутентификацией
- ✅ CSRF защита включена (Flask-WTF)
- ✅ Rate limiting настроен (Flask-Limiter)
- ✅ Валидация данных реализована
- ✅ Параметризованные SQL запросы (защита от SQL injection)

Подробнее: [docs/API_SECURITY_AUDIT_REPORT.md](API_SECURITY_AUDIT_REPORT.md)

## RBAC (роли и права доступа)

Права доступа проверяются через декоратор `@permission_required('permission_name')`.

### Стандартные роли

- `viewer` — просмотр
- `master` — работа с заявками (в рамках прав)
- `manager` — расширенные права (включая часть управления)
- `admin` — полный доступ

### Индивидуальные роли для сотрудников

Для мастеров и менеджеров поддерживаются **кастомные роли** вида:
- `master_{id}`
- `manager_{id}`

Они создаются/обновляются с выбранным набором `permission_ids` и хранятся в `role_permissions`.

### Новые permissions (миграция 035)

- `view_finance`, `manage_finance`
- `view_shop`, `manage_shop`
- `view_action_logs`
- `manage_statuses`

### Важные ограничения безопасности

- **Кастомные роли сотрудников** (`master_{id}`, `manager_{id}`) **не могут** получать права:
  - `manage_users`
  - `manage_settings`
  Даже если попытаться назначить их через API/UI, сервер вернет `400`.

### Проверка прав (скрипты)

- Список прав и назначений ролям:
  - `python scripts/audit_permissions.py`
- Проверка конкретного пользователя:
  - `python scripts/check_user_permissions.py <username>`

### Матрица прав по модулям (основные)

- **Склад**
  - просмотр: `view_warehouse`
  - изменения: `manage_warehouse`
- **Финансы**
  - просмотр: `view_finance`
  - изменения: `manage_finance`
- **Магазин**
  - просмотр: `view_shop`
  - изменения/возвраты/удаление: `manage_shop`
- **Логи действий**
  - просмотр: `view_action_logs`
- **Статусы**
  - чтение списка статусов: `view_orders`
  - управление статусами: `manage_statuses`

### Важно про Orders API (сегодняшнее усиление)

В `app/routes/orders.py` включен server-side RBAC-гейт для `/api/*` этого blueprint:
- `GET` → требует `view_orders`
- `POST/PUT/PATCH/DELETE` → требует `edit_orders`

### Единые RBAC-гейты для API модулей

Для API модулей включены унифицированные server-side проверки с JSON-ответами (`401 auth_required`, `403 forbidden`):
- `finance` (`/finance/api/*`):
  - `GET/HEAD/OPTIONS` → `view_finance`
  - `POST/PUT/PATCH/DELETE` → `manage_finance`
- `warehouse` (`/warehouse/api/*`, `/api/warehouse/*`):
  - `GET/HEAD/OPTIONS` → `view_warehouse`
  - `POST/PUT/PATCH/DELETE` → `manage_warehouse`
- `shop` (`/shop/api/*`):
  - `GET/HEAD/OPTIONS` → `view_shop`
  - `POST/PUT/PATCH/DELETE` → `manage_shop`
- `reports` (`/reports/api/*`):
  - `GET` → `view_reports`
- `generic api` (`/api/*` в `app/routes/api.py`):
  - `GET/HEAD/OPTIONS` → `view_orders`
  - `POST/PUT/PATCH/DELETE` → `edit_orders`

### Новые важные endpoints

- **Отправка сводного отчёта руководителю**  
  `POST /reports/api/dashboard/send-to-director`  
  Отправляет HTML-отчёт по сводному дашборду на email директора из настроек.  
  - Тело (JSON):  
    - `preset` (string, optional) — период-пресет (`today`, `yesterday`, `last_7_days`, `current_month` и т.п.)  
    - `date_from`, `date_to` (string, optional, `YYYY-MM-DD`) — явный период; при наличии имеют приоритет над `preset`  
  - Ответ:  
    - `200` `{ "success": true, "message": "..." }` при успехе  
    - `4xx/5xx` с `success=false` и `error` при ошибке (настройки почты, отсутствие email директора и т.п.)  
  - Доступ: `view_reports`

- **Перевод между кассами (Наличные ↔ Перевод и др.)**  
  `POST /finance/api/transfer-between-methods`  
  Создаёт пару кассовых операций: расход с одного способа оплаты и приход на другой (внутренний перевод, не попадает в «Приход/Расход за период»).  
  - Тело (JSON):  
    - `from_method` (string, required) — способ списания (`cash`, `transfer`, `card` или кастомный)  
    - `to_method` (string, required) — способ зачисления  
    - `amount` (number, required, > 0) — сумма перевода  
    - `transaction_date` (string, optional, `YYYY-MM-DD`) — дата операции; по умолчанию — сегодня (по Москве)  
    - `description` (string, optional) — комментарий; добавляется к системному описанию `Перевод между кассами: from → to`  
  - Ответ:  
    - `200` `{ "success": true, "id_expense": <int>, "id_income": <int>, "message": "..." }`  
    - `400` при ошибке валидации (`amount <= 0`, одинаковые методы, неверный способ оплаты и т.п.)  
  - Доступ: `manage_finance`

## Периоды в отчетах (preset/date_from/date_to)

Многие страницы и API поддерживают единый формат периода:
- `preset` — пресет (например `today`, `yesterday`, `last_7_days`, `last_30_days`, `current_month`, `last_month`, `year_to_date`)
- `date_from`, `date_to` — произвольный диапазон (`YYYY-MM-DD`)

Правила:
- если задан `date_from` или `date_to` — применяется кастомный диапазон (preset игнорируется)
- если задана только одна граница — она зеркалится во вторую
- **по умолчанию** диапазон заканчивается **сегодняшним днём** (в т.ч. пресеты «Квартал», «Полгода»)

Примечание UI:
- быстрые кнопки периода на страницах отчетов/дашборда формируют `date_from/date_to`
- `preset` используется в `/reports/dashboard` и `/api/dashboard` для совместимости

## Формат ответов

### Успешный ответ

```json
{
  "success": true,
  "data": {...}
}
```

### Ошибка

```json
{
  "success": false,
  "error": "Сообщение об ошибке",
  "error_type": "validation|not_found|database|permission"
}
```

## Коды HTTP статусов

- `200` - Успешный запрос
- `201` - Ресурс создан
- `400` - Ошибка валидации
- `403` - Недостаточно прав
- `404` - Ресурс не найден
- `500` - Внутренняя ошибка сервера

## API Endpoints

### Заявки (Orders)

#### GET /all_orders

Получение списка заявок.

**Параметры запроса:**
- `status` (string, optional) - код статуса (new, in_progress, completed, closed)
- `status_id` (int, optional) - ID статуса
- `customer_id` (int, optional) - ID клиента
- `device_id` (int, optional) - ID устройства
- `manager_id` (int, optional) - ID менеджера
- `master_id` (int, optional) - ID мастера
- `search` (string, optional) - поисковый запрос
- `date_from` (string, optional) - дата начала (YYYY-MM-DD)
- `date_to` (string, optional) - дата окончания (YYYY-MM-DD)
- `page` (int, optional) - номер страницы (по умолчанию 1)
- `per_page` (int, optional) - элементов на странице (по умолчанию 50)
- `sort_by` (string, optional) - поле сортировки
- `sort_order` (string, optional) - направление (ASC/DESC)

**Пример:**
```
GET /all_orders?status=new&page=1&per_page=50
```

**Ответ:** HTML страница со списком заявок

#### GET /api/datatables/orders

Источник данных для таблицы реестра заявок (Server-Side DataTables на странице `/all_orders?view=registry`).

**Параметры запроса:** те же, что у фильтров реестра, плюс параметры DataTables:
- `draw`, `start`, `length` — пагинация DataTables
- `search[value]` — поисковая строка
- `status`, `manager`, `master`, `date_from`, `date_to` — фильтры

**Ответ (JSON):**
```json
{
  "draw": 1,
  "recordsTotal": 100,
  "recordsFiltered": 25,
  "data": [
    {
      "order_id": "uuid",
      "id_col": "<html>",
      "status_col": "<html>",
      "client_col": "<html>",
      "device_col": "<html>",
      "brand_col": "<html>",
      "symptoms_col": "<html>",
      "appearance_col": "<html>",
      "master_col": "<html>",
      "manager_col": "<html>",
      "created_at_col": "<html>",
      "total_col": "1 234.56 ₽",
      "paid_col": "1 000.00 ₽",
      "debt_col": "234.56 ₽",
      "services_total_col": "<html>",
      "parts_total_col": "<html>",
      "prepayment_col": "<html>",
      "serial_number_col": "<html>",
      "email_col": "<html>",
      "comment_col": "<html>",
      "updated_at_col": "<html>",
      "comments_count_col": "<html>"
    }
  ]
}
```

Суммы (total, paid, debt, services_total, parts_total, prepayment) считаются на бэкенде через batch-запрос по заявкам текущей страницы (логика как в карточке заявки). Состояние таблицы в браузере: видимость колонок — `localStorage.ordersTableColumns`, порядок колонок — `localStorage.ordersTableColumnOrder`.

#### GET /order/<order_id>

Получение деталей заявки.

**Параметры:**
- `order_id` (string) — UUID заявки **или** внутренний числовой id заявки. Сначала выполняется поиск по UUID (`orders.order_id`), при отсутствии — по внутреннему id (`orders.id`). Это позволяет открывать заявку по ссылкам из кассы и отчётов.

**Примеры:**
```
GET /order/28bc9fe9-2198-45e1-b55f-ff7a72f0235b
GET /order/4617
```

**Ответ:** HTML страница с деталями заявки

#### POST /order/<order_id>

Редактирование заявки (форма).

**Параметры:**
- `order_id` (string) - UUID заявки

**Тело запроса (form-data):**
- `device_type` (int, optional) - ID типа устройства
- `device_brand` (int, optional) - ID бренда устройства
- `model` (string, optional) - модель устройства (автопоиск из `order_models`)
- `serial_number` (string, optional) - серийный номер
- `password` (string, optional) - пароль от устройства
- `appearance` (string, optional) - внешний вид (теги через запятую, разделители: запятая, точка с запятой, перенос строки)
- `symptom_tags` (string, optional) - теги симптомов (неисправности через запятую, разделители: запятая, точка с запятой, перенос строки)

**Примечание:** Система автоматически:
- Парсит строки симптомов и внешнего вида
- Создает связи в таблицах `order_symptoms` и `order_appearance_tags` (many-to-many)
- Автоматически создает новые значения в справочниках, если их нет
- Сохраняет старые поля (`symptom_tags`, `appearance`) для обратной совместимости
- `manager` (int, optional) - ID менеджера
- `master` (int, optional) - ID мастера
- `prepayment` (float, optional) - предоплата
- `comment` (string, optional) - комментарий

**Ответ:** Redirect на страницу заявки с сообщением об успехе

**Особенности:**
- Все поля опциональны - обновляются только переданные поля
- Поле `model` поддерживает автопоиск и автоматическое создание новых моделей
- При обновлении устройства также обновляется связанное устройство (если указано)

#### POST /add_order

Создание новой заявки (форма).

**Тело запроса (form-data):**
- `client_name` (string, required) - имя клиента
- `phone` (string, required) - телефон
- `email` (string, optional) - email
- `device_type` (int, required) - ID типа устройства
- `device_brand` (int, required) - ID бренда устройства
- `serial_number` (string, optional) - серийный номер
- `manager` (int, required) - ID менеджера
- `master` (int, optional) - ID мастера
- `prepayment` (float, optional) - предоплата
- `password` (string, optional) - пароль от устройства
- `appearance` (string, optional) - внешний вид (теги через запятую)
- `comment` (string, optional) - комментарий
- `symptom_tags` (string, optional) - теги симптомов (неисправности через запятую)
- `model` (string, optional) - модель устройства (автопоиск из `order_models`)

**Ответ:** Redirect на страницу заявки

#### PUT /api/order/<order_id>/status

Обновление статуса заявки.

**Тело запроса (JSON):**
```json
{
  "status_id": 2,
  "comment": "Комментарий к смене статуса (опционально)"
}
```

**Ответ:**
```json
{
  "success": true,
  "status_id": 2,
  "status_name": "В работе",
  "status_color": "#007bff",
  "triggers_payment_modal": false,
  "accrues_salary": false,
  "blocks_edit": false,
  "requires_warranty": false,
  "requires_comment": false
}
```

#### POST /api/orders/check_duplicate

Проверка дубликатов заявок.

**Тело запроса (JSON):**
```json
{
  "phone": "+79991234567",
  "serial_number": "SN123456"
}
```

**Ответ:**
```json
{
  "success": true,
  "duplicates": false
}
```

#### POST /api/order/<order_id>/toggle-visibility

Скрытие/показ заявки.

**Тело запроса (JSON):**
```json
{
  "hidden": true,
  "reason": "Причина скрытия"
}
```

**Ответ:**
```json
{
  "success": true,
  "hidden": true
}
```

### Услуги заявки

#### GET /api/orders/<order_id>/services

Получение услуг заявки.

**Ответ:**
```json
[
  {
    "id": 1,
    "service_id": 1,
    "service_name": "Диагностика",
    "quantity": 1,
    "price": 1000.00
  }
]
```

#### POST /api/orders/<order_id>/services

Добавление услуги к заявке.

**Тело запроса (JSON):**
```json
{
  "service_id": 1,
  "quantity": 1,
  "price": 1000.00
}
```

**Ответ:**
```json
{
  "success": true,
  "id": 1
}
```

#### DELETE /api/order-services/<order_service_id>

Удаление услуги из заявки.

**Ответ:**
```json
{
  "success": true
}
```

### Запчасти заявки

#### GET /api/orders/<order_id>/parts

Получение запчастей заявки.

**Ответ:**
```json
[
  {
    "id": 1,
    "part_id": 1,
    "part_name": "Экран",
    "part_number": "SCR001",
    "quantity": 1,
    "price": 5000.00
  }
]
```

#### POST /api/orders/<order_id>/parts

Добавление запчасти к заявке.

**Тело запроса (JSON):**
```json
{
  "part_id": 1,
  "quantity": 1,
  "price": 5000.00
}
```

**Ответ:**
```json
{
  "success": true,
  "id": 1
}
```

#### DELETE /api/order-parts/<order_part_id>

Удаление запчасти из заявки.

**Ответ:**
```json
{
  "success": true
}
```

### Оплаты

#### GET /api/orders/<order_id>/payments

Получение оплат заявки.

**Ответ:**
```json
[
  {
    "id": 1,
    "amount": 5000.00,
    "payment_type": "cash",
    "kind": "payment",
    "status": "captured",
    "username": "admin",
    "comment": "Предоплата",
    "created_at": "2025-11-30T10:00:00"
  }
]
```

**Поля:**
- `kind` - тип платежа: `payment` (обычная оплата), `deposit` (предоплата), `refund` (возврат), `adjustment` (корректировка)
- `status` - статус: `pending` (ожидает), `captured` (подтверждён), `cancelled` (отменён), `refunded` (возвращён)

#### POST /api/orders/<order_id>/payments

Добавление оплаты к заявке.

**Тело запроса (JSON):**
```json
{
  "amount": 5000.00,
  "payment_type": "cash",
  "comment": "Предоплата",
  "kind": "payment",
  "status": "captured",
  "idempotency_key": "unique-key-123"
}
```

**Параметры:**
- `amount` (float, required) - сумма оплаты
- `payment_type` (string, required) - тип оплаты: `cash` (наличные), `card` (карта), `transfer` (перевод)
- `comment` (string, optional) - комментарий
- `kind` (string, optional) - тип платежа (по умолчанию `payment`)
- `status` (string, optional) - статус (по умолчанию `captured`)
- `idempotency_key` (string, optional) - ключ идемпотентности для защиты от дублирования

**Ответ:**
```json
{
  "success": true,
  "id": 1
}
```

**Особенности:**
- При добавлении оплаты автоматически создается кассовая операция в `cash_transactions` (кроме `payment_type='wallet'`)
- Кассовая операция связана с оплатой через `payment_id`
- Оплата отображается в финансовых отчетах и модуле кассы
- При `payment_type='wallet'` деньги списываются с кошелька клиента без создания кассовой операции

#### DELETE /api/payments/<payment_id>

Отмена оплаты (мягкое удаление).

**Тело запроса (JSON):**
```json
{
  "reason": "Причина отмены оплаты"
}
```

**Требования:**
- Роль `manager` или выше
- Обязательное поле `reason` (причина отмены)

**Ответ:**
```json
{
  "success": true
}
```

**Особенности:**
- Оплата помечается как `cancelled` (не удаляется физически)
- Создаётся сторно-операция в кассе для отменённых платежей
- История платежа сохраняется для аудита

#### POST /api/payments/<payment_id>/refund

Возврат оплаты.

**Тело запроса (JSON):**
```json
{
  "amount": 1000.00,
  "reason": "Причина возврата",
  "create_receipt": true
}
```

**Требования:**
- Роль `manager` или выше
- `amount` не может превышать оставшуюся сумму оригинальной оплаты

**Ответ:**
```json
{
  "success": true,
  "refund_payment_id": 2,
  "receipt_id": 1,
  "payments": [...],
  "order_total": 5000.00,
  "order_paid": 4000.00,
  "order_debt": 1000.00
}
```

**Особенности:**
- Создаётся новый платеж с `kind='refund'`
- Создаётся расходная кассовая операция
- Сумма возврата ограничена оставшейся суммой оригинальной оплаты
- Опционально создаётся чек возврата

#### POST /api/payments/<payment_id>/refund_to_wallet
#### GET /api/orders/<order_id>/wallet
#### POST /api/orders/<order_id>/wallet
#### POST /api/orders/<order_id>/overpayment_to_wallet

Депозитные операции в заявках отключены.

**Текущий ответ:**
```json
{
  "success": false,
  "error": "Функционал депозита в заявках отключен"
}
```

**HTTP статус:** `410 Gone`

#### GET /api/payments/<payment_id>/receipts
#### POST /api/payments/<payment_id>/receipts

Работа с чеками по оплате.

**GET** - получение списка чеков:
```json
{
  "success": true,
  "receipts": [
    {
      "id": 1,
      "receipt_type": "sell",
      "created_at": "2025-12-20T10:00:00",
      "created_by": "admin"
    }
  ]
}
```

**POST** - создание чека:
```json
{
  "receipt_type": "sell"
}
```

**Параметры:**
- `receipt_type` - тип чека: `sell` (продажа), `refund` (возврат)

**Требования:**
- Роль `manager` или выше для создания чека

**Ответ:**
```json
{
  "success": true,
  "receipt_id": 1,
  "receipts": [...]
}
```

### Комментарии

#### POST /api/order/<order_id>/comment

Добавление комментария к заявке.

**Тело запроса (JSON):**
```json
{
  "author_name": "admin",
  "comment_text": "Клиент согласен на ремонт"
}
```

**Ответ:**
```json
{
  "success": true,
  "comment_id": 1,
  "comments": [...]
}
```

#### DELETE /api/order/comment/<comment_id>

Удаление комментария.

**Ответ:**
```json
{
  "success": true
}
```

### Клиенты

#### GET /clients

Получение списка клиентов.

**Параметры запроса:**
- `q` (string, optional) - поисковый запрос
- `page` (int, optional) - номер страницы

**Пример:**
```
GET /clients?q=Иван&page=1
```

**Ответ:** HTML страница со списком клиентов

#### GET /clients/<client_id>

Получение деталей клиента.

**Ответ:** HTML страница с деталями клиента

#### GET /api/customers/lookup

Поиск клиента по телефону.

**Параметры запроса:**
- `phone` (string, required) - номер телефона

**Пример:**
```
GET /api/customers/lookup?phone=+79991234567
```

**Ответ:**
```json
{
  "success": true,
  "found": true,
  "customer": {
    "id": 1,
    "name": "Иван Иванов",
    "phone": "79991234567",
    "email": "ivan@example.com"
  },
  "devices": [...]
}
```

#### POST /api/customers

Создание нового клиента.

**Требования:**
- Право доступа: `create_customers`
- Аутентификация: требуется

**Тело запроса (JSON):**
```json
{
  "name": "Иван Иванов",
  "phone": "+79991234567",
  "email": "ivan@example.com"
}
```

**Параметры:**
- `name` (string, required) - Имя клиента
- `phone` (string, required) - Телефон клиента (автоматически нормализуется)
- `email` (string, optional) - Email клиента

**Ответ:**
```json
{
  "success": true,
  "customer": {
    "id": 123,
    "name": "Иван Иванов",
    "phone": "79991234567",
    "email": "ivan@example.com"
  }
}
```

**Особенности:**
- При создании нового клиента система **автоматически генерирует пароль** для доступа к порталу
- Пароль состоит из 8 символов (буквы и цифры)
- Пароль сохраняется в зашифрованном виде в базе данных
- При первом входе клиент должен будет сменить пароль

#### PUT /api/customers/<client_id>

Обновление данных клиента.

**Требования:**
- Право доступа: `edit_customers`
- Аутентификация: требуется

**Тело запроса (JSON):**
```json
{
  "name": "Иван Петров",
  "phone": "+79991234567",
  "email": "ivan@example.com"
}
```

**Ответ:**
```json
{
  "success": true,
  "customer": {...}
}
```

#### POST /api/clients/<client_id>/devices

Добавление устройства клиенту.

**Тело запроса (JSON):**
```json
{
  "device_type_id": 1,
  "device_brand_id": 1,
  "serial_number": "SN123456"
}
```

**Ответ:**
```json
{
  "success": true,
  "device": {...},
  "devices": [...]
}
```

### Справочники

Все справочники имеют единый API интерфейс.

**Нормализация данных (Миграция 013):**
- Модели устройств хранятся в `orders.model_id` (FK к `order_models`) вместо текста
- Симптомы связаны через таблицу `order_symptoms` (many-to-many) вместо текста через запятую
- Теги внешнего вида связаны через таблицу `order_appearance_tags` (many-to-many) вместо текста через запятую
- Старые поля (`model`, `symptom_tags`, `appearance`) сохранены для обратной совместимости
- При создании/обновлении заявки система автоматически:
  - Парсит строки симптомов и внешнего вида
  - Создает связи в нормализованных таблицах
  - Автоматически создает новые значения в справочниках, если их нет
  - Сохраняет старые поля для обратной совместимости

#### Типы устройств

- `GET /device-types` - список типов устройств
- `POST /device-types` - создание типа устройства
- `PUT /device-types/<id>` - обновление типа устройства
- `DELETE /device-types/<id>` - удаление типа устройства
- `POST /device-types/update-sort-order` - обновление порядка сортировки

**Пример создания:**
```json
POST /device-types
{
  "name": "Ноутбук",
  "sort_order": 1
}
```

**Ответ:**
```json
{
  "success": true,
  "id": 1
}
```

#### Бренды устройств

- `GET /device-brands` - список брендов
- `POST /device-brands` - создание бренда
- `PUT /device-brands/<id>` - обновление бренда
- `DELETE /device-brands/<id>` - удаление бренда
- `POST /device-brands/update-sort-order` - обновление порядка сортировки

#### Менеджеры

- `GET /managers` - список менеджеров
- `POST /managers` - создание менеджера
- `PUT /managers/<id>` - обновление менеджера
- `DELETE /managers/<id>` - удаление менеджера

#### Мастера

- `GET /masters` - список мастеров
- `POST /masters` - создание мастера
- `PUT /masters/<id>` - обновление мастера
- `DELETE /masters/<id>` - удаление мастера

#### Симптомы

- `GET /symptoms` - список симптомов
- `POST /symptoms` - создание симптома
- `PUT /symptoms/<id>` - обновление симптома
- `DELETE /symptoms/<id>` - удаление симптома
- `POST /symptoms/update-sort-order` - обновление порядка сортировки

#### Теги внешнего вида

- `GET /appearance-tags` - список тегов
- `POST /appearance-tags` - создание тега
- `PUT /appearance-tags/<id>` - обновление тега
- `DELETE /appearance-tags/<id>` - удаление тега
- `POST /appearance-tags/update-sort-order` - обновление порядка сортировки

#### Модели устройств

- `GET /order-models` - список моделей устройств
- `POST /order-models` - создание модели (автоматически нормализует название)

**Пример создания:**
```json
POST /order-models
{
  "name": "iPhone 14 Pro"
}
```

**Ответ:**
```json
{
  "success": true,
  "id": 1,
  "name": "iPhone 14 Pro"
}
```

**Особенности:**
- Модели хранятся в таблице `order_models`
- Название автоматически нормализуется (первая буква заглавная)
- Если модель уже существует, возвращается существующая запись
- Модель сохраняется в поле `model_id` таблицы `orders` (FK к `order_models`)
- Поле `model` (TEXT) также сохраняется для обратной совместимости
- **Нормализация:** Модели связаны через FK, что обеспечивает целостность данных и быстрый поиск

#### Услуги

- `GET /services` - список услуг
- `POST /services` - создание услуги
- `PUT /services/<id>` - обновление услуги
- `DELETE /services/<id>` - удаление услуги
- `POST /services/update-sort-order` - обновление порядка сортировки

**Пример создания:**
```json
POST /services
{
  "name": "Диагностика",
  "price": 1000.00,
  "is_default": 1,
  "sort_order": 1
}
```

#### Запчасти

- `GET /parts` - список запчастей
- `POST /parts` - создание запчасти
- `PUT /parts/<id>` - обновление запчасти
- `DELETE /parts/<id>` - удаление запчасти

**Пример создания:**
```json
POST /parts
{
  "name": "Экран",
  "part_number": "SCR001",
  "price": 5000.00,
  "stock_quantity": 10,
  "min_quantity": 5,
  "category": "Экраны",
  "supplier": "Поставщик 1"
}
```

#### Статусы заявок

- `GET /api/statuses` - список статусов
- `POST /api/statuses` - создание статуса
- `PATCH /api/statuses/<status_id>` - обновление статуса
- `DELETE /api/statuses/<status_id>` - удаление статуса

**Пример создания:**
```json
POST /api/statuses
{
  "code": "new",
  "name": "Новая",
  "color": "#007bff",
  "group_name": "Новые",
  "is_default": 1,
  "sort_order": 1,
  "triggers_payment_modal": 0,
  "accrues_salary": 0,
  "is_final": 0,
  "blocks_edit": 0,
  "requires_warranty": 0,
  "requires_comment": 0,
  "is_archived": 0
}
```

**Поля флагов:**
- `triggers_payment_modal` - вызывает окно оплаты при смене статуса
- `accrues_salary` - начисляет зарплату при смене статуса
- `is_final` - финальный статус (закрывает заявку)
- `blocks_edit` - запрещает редактирование заявки
- `requires_warranty` - требует указать гарантию
- `requires_comment` - требует комментарий при смене статуса
- `is_archived` - архивный статус (скрыт из списков)

### Логи действий (Action Logs)

#### GET /action-logs

Получение списка действий пользователей.

**Параметры запроса:**
- `action_type` (string, optional) - тип действия (create, update, delete, sell, add_service, remove_service, add_payment, delete_payment, add_comment, delete_comment, restore)
- `entity_type` (string, optional) - тип объекта (order, customer, device, payment, service)
- `entity_id` (int, optional) - ID объекта
- `date_from` (string, optional) - дата начала (YYYY-MM-DD)
- `date_to` (string, optional) - дата окончания (YYYY-MM-DD)
- `page` (int, optional) - номер страницы (по умолчанию 1)
- `per_page` (int, optional) - элементов на странице (по умолчанию 50)

**Пример:**
```
GET /action-logs?action_type=update&entity_type=order&page=1&per_page=50
```

**Ответ:** HTML страница со списком действий

**Особенности:**
- Автоматическое логирование всех действий пользователей
- Улучшенное отображение изменений статуса: показываются названия статусов вместо ID
- Отображение изменений менеджера и мастера с названиями
- Ссылки на реальные объекты (заявки, клиенты, устройства)
- Ссылки на историю устройства в логах создания устройства (`/device/<device_id>`)
- Фильтры склада удалены из интерфейса (операции со складом логируются в `/warehouse/logs`)

### Склад (Warehouse)

#### GET /warehouse/parts

Получение списка товаров.

**Параметры запроса:**
- `q` (string, optional) - поисковый запрос (регистронезависимый, по всем словам)
- `category` (int, optional) - ID категории
- `low_stock` (boolean, optional) - только товары с низким остатком
- `sort_by` (string, optional) - поле сортировки (name, part_number, category, stock_quantity, price)
- `sort_order` (string, optional) - направление (ASC/DESC)
- `page` (int, optional) - номер страницы
- `per_page` (int, optional) - элементов на странице

**Пример:**
```
GET /warehouse/parts?q=экран&category=1&sort_by=name&sort_order=ASC
```

**Ответ:** HTML страница со списком товаров

#### GET /warehouse/parts/<part_id>

Получение деталей товара.

**Ответ:** HTML страница с деталями товара

#### POST /warehouse/parts/new

Создание нового товара.

**Тело запроса (form-data):**
- `name` (string, required) - название товара
- `category_id` (int, optional) - ID категории
- `part_number` (string, required) - артикул (неизменяемый после создания)
- `unit` (string, optional) - единица измерения (по умолчанию "Штуки")
- `stock_quantity` (float, optional) - начальный остаток
- `price` (float, required) - розничная цена
- `purchase_price` (float, optional) - закупочная цена
- `warranty_days` (int, optional) - гарантия в днях
- `comment` (string, optional) - комментарий

**Ответ:** Редирект на страницу товара

#### POST /warehouse/parts/<part_id>/edit

Обновление товара.

**Тело запроса (form-data):** аналогично созданию (кроме `part_number`)

**Ответ:** Редирект на страницу товара

#### POST /warehouse/parts/<part_id>/delete

Мягкое удаление товара.

**Ответ:** JSON с результатом

#### POST /warehouse/parts/<part_id>/restore

Восстановление удаленного товара.

**Ответ:** JSON с результатом

#### POST /warehouse/parts/<part_id>/income

Оприходование товара.

**Тело запроса (JSON):**
```json
{
  "quantity": 10,
  "notes": "Поступление от поставщика"
}
```

**Ответ:** JSON с результатом

#### POST /warehouse/parts/<part_id>/expense

Списание товара.

**Тело запроса (JSON):**
```json
{
  "quantity": 5,
  "notes": "Списание на ремонт"
}
```

**Ответ:** JSON с результатом

#### GET /warehouse/logs

Получение истории операций со складом.

**Параметры запроса:**
- `operation_type` (string, optional) - тип операции (create, update, delete, restore, income, expense, category_create, category_update, category_delete)
- `part_id` (int, optional) - ID товара
- `category_id` (int, optional) - ID категории
- `date_from` (string, optional) - дата начала
- `date_to` (string, optional) - дата окончания
- `page` (int, optional) - номер страницы
- `per_page` (int, optional) - элементов на странице

**Ответ:** HTML страница с историей операций

#### GET /warehouse/movements

Получение движений товаров.

**Параметры запроса:**
- `movement_type` (string, optional) - тип движения (income, expense, sale, return, adjustment_increase, adjustment_decrease)
- `operation_category` (string, optional) - категория операции (manual, automatic)
- `part_id` (int, optional) - ID товара
- `date_from` (string, optional) - дата начала
- `date_to` (string, optional) - дата окончания
- `page` (int, optional) - номер страницы

**Ответ:** HTML страница с движениями

### Поставщики (Suppliers)

#### GET /warehouse/suppliers

Получение списка поставщиков.

**Ответ:** HTML страница со списком поставщиков

#### GET /warehouse/suppliers/<supplier_id>

Получение деталей поставщика.

**Ответ:** HTML страница с деталями поставщика

#### GET /warehouse/suppliers/new

Форма создания нового поставщика.

**Ответ:** HTML форма

#### POST /warehouse/suppliers/new

Создание нового поставщика.

**Тело запроса (JSON):**
```json
{
  "name": "ООО Поставщик",
  "contact_person": "Иван Иванов",
  "phone": "+79991234567",
  "email": "supplier@example.com",
  "address": "г. Москва, ул. Примерная, д. 1",
  "notes": "Основной поставщик экранов"
}
```

**Ответ:** JSON с результатом

#### GET /warehouse/suppliers/<supplier_id>/edit

Форма редактирования поставщика.

**Ответ:** HTML форма

#### POST /warehouse/suppliers/<supplier_id>/edit

Обновление поставщика.

**Тело запроса (JSON):** аналогично созданию

**Ответ:** JSON с результатом

#### POST /warehouse/suppliers/<supplier_id>/delete

Удаление поставщика (мягкое удаление, is_active = 0).

**Ответ:** JSON с результатом

### Инвентаризация (Inventory)

#### GET /warehouse/inventory

Получение списка инвентаризаций.

**Параметры запроса:**
- `status` (string, optional) - статус (draft, completed)
- `date_from` (string, optional) - дата начала
- `date_to` (string, optional) - дата окончания

**Ответ:** HTML страница со списком инвентаризаций

#### GET /warehouse/inventory/new

Форма создания новой инвентаризации.

**Ответ:** HTML форма

#### POST /warehouse/inventory/new

Создание новой инвентаризации.

**Тело запроса (JSON):**
```json
{
  "inventory_date": "2025-12-21",
  "items": [
    {
      "part_id": 1,
      "expected_quantity": 10,
      "actual_quantity": 12
    },
    {
      "part_id": 2,
      "expected_quantity": 5,
      "actual_quantity": 3
    }
  ],
  "notes": "Плановая инвентаризация"
}
```

**Ответ:** JSON с результатом

#### GET /warehouse/inventory/<inventory_id>

Получение деталей инвентаризации.

**Ответ:** HTML страница с деталями инвентаризации

#### POST /warehouse/inventory/<inventory_id>/complete

Завершение инвентаризации (применение корректировок остатков).

**Ответ:** JSON с результатом

**Примечание:** При завершении инвентаризации автоматически создаются движения товаров (adjustment_increase или adjustment_decrease) и записи в истории склада.

### Категории товаров

#### GET /warehouse/categories

Получение списка категорий (иерархическая структура).

**Ответ:** JSON с деревом категорий

#### POST /warehouse/categories/new

Создание категории.

**Тело запроса (JSON):**
```json
{
  "name": "Экраны",
  "parent_id": null
}
```

**Ответ:** JSON с результатом

#### POST /warehouse/categories/<category_id>/update

Обновление категории.

**Тело запроса (JSON):**
```json
{
  "name": "Экраны для ноутбуков",
  "parent_id": 1
}
```

**Ответ:** JSON с результатом

#### POST /warehouse/categories/<category_id>/delete

Удаление категории (только если нет товаров и подкатегорий).

**Ответ:** JSON с результатом

## Обработка ошибок

Все API endpoints возвращают единообразные ответы об ошибках:

### ValidationError (400)

```json
{
  "success": false,
  "error": "Номер телефона обязателен",
  "error_type": "validation"
}
```

### NotFoundError (404)

```json
{
  "success": false,
  "error": "Заявка с ID 999 не найдена",
  "error_type": "not_found"
}
```

### PermissionError (403)

```json
{
  "success": false,
  "error": "У вас нет прав для выполнения этого действия",
  "error_type": "permission"
}
```

### DatabaseError (500)

```json
{
  "success": false,
  "error": "Ошибка базы данных",
  "error_type": "database"
}
```

---

## Зарплата (Salary)

### GET /salary

Главная страница модуля зарплаты.

**Ответ:** HTML страница

### GET /api/salary/report

Отчёт по зарплате (данные для страницы «Отчёты» → «Зарплата»).

**Параметры запроса:**
- `date_from` (YYYY-MM-DD, optional)
- `date_to` (YYYY-MM-DD, optional)
- `role` (master|manager, optional)
- `master_id` (int, optional)
- `manager_id` (int, optional)

**Ответ (JSON):**
```json
{
  "success": true,
  "report": {
    "summary": {
      "total_accruals": 10,
      "total_amount_cents": 50000,
      "total_profit_cents": 120000,
      "total_revenue_cents": 350000,
      "total_owner_net_cents": 180000,
      "unique_users": 3
    },
    "accruals": [
      {
        "order_id": 123,
        "order_uuid": "...",
        "revenue_cents": 34300,
        "order_profit_cents": 15000,
        "owner_net_cents": 12000,
        "amount_cents": 3000,
        "master_name": "...",
        "manager_name": "...",
        "role": "master",
        "created_at": "..."
      }
    ],
    "date_from": "2026-01-01",
    "date_to": "2026-01-31"
  }
}
```

Выручка и прибыль считаются **на уровне заявки** (одни значения для всех начислений по одной заявке). В сводке: `total_revenue_cents` — сумма выручки по заявкам за период, `total_owner_net_cents` — итого руководителю (выручка − себестоимость − зарплата).

### GET /salary/employee/<employee_id>/<role>

Личный кабинет сотрудника.

**Параметры:**
- `employee_id` (int)
- `role` (master | manager)

**Ответ:** HTML страница

### GET /api/salary/employees

Список сотрудников с агрегированной статистикой.

**Параметры запроса:**
- `date_from` (YYYY-MM-DD, optional)
- `date_to` (YYYY-MM-DD, optional)
- `role` (master|manager, optional)
- `status` (active|inactive, optional)
- `sort_by` (profit|revenue|orders|salary, optional)

**Ответ:**
```json
{
  "success": true,
  "employees": [
    {
      "employee_id": 1,
      "employee_name": "Иван",
      "role": "master",
      "profit_cents": 120000,
      "revenue_cents": 350000,
      "orders_count": 4,
      "salary_accrued_cents": 50000,
      "salary_paid_cents": 10000,
      "salary_bonuses_cents": 5000,
      "salary_fines_cents": 0,
      "salary_owed_cents": 45000,
      "rank": 1
    }
  ]
}
```

### GET /api/salary/employee/<employee_id>/<role>

Данные кабинета сотрудника за период.

**Параметры запроса:**
- `period` (today|yesterday|week|month|year|custom)
- `date_from` (YYYY-MM-DD, для custom)
- `date_to` (YYYY-MM-DD, для custom)

### POST /api/salary/employee/<employee_id>/<role>/bonus

Начисление премии.

**Тело запроса (JSON):**
```json
{
  "amount": 500,
  "reason": "За качество",
  "bonus_date": "2026-01-20",
  "order_id": 123
}
```

### POST /api/salary/employee/<employee_id>/<role>/fine

Начисление штрафа.

**Тело запроса (JSON):**
```json
{
  "amount": 1000,
  "reason": "Опоздание",
  "fine_date": "2026-01-20",
  "order_id": 123
}
```

### POST /api/salary/employee/<employee_id>/<role>/payment

Регистрация выплаты зарплаты.

**Тело запроса (JSON):**
```json
{
  "amount": 1500,
  "payment_date": "2026-01-20",
  "payment_type": "salary",
  "period_start": "2026-01-01",
  "period_end": "2026-01-31",
  "comment": "Выплата"
}
```

### POST /api/salary/employee/<employee_id>/<role>/writeoff

Списание долга сотрудника (без кассы).

**Тело запроса (JSON):**
```json
{
  "amount": 500,
  "reason": "Списание долга"
}
```

### POST /api/salary/recalculate/<order_id>

Принудительный пересчёт зарплаты по заявке (удаляет существующие начисления и создаёт новые по текущим правилам и данным заявки). Используется для исправления данных или при изменении правил начисления.

**Поведение начисления при смене статуса:** при обычной смене статуса заявки на статус с флагом `accrues_salary` зарплата начисляется **только если по заявке ещё нет начислений**. Повторный переход «Закрыто → В работе → Закрыто» не создаёт дубликатов. Эндпоинт `recalculate` всегда выполняет пересчёт (аналог `force_recalculate=True`).

**Параметры:**
- `order_id` (int) — ID заявки

**Ответ:**
```json
{
  "success": true,
  "accrual_ids": [1, 2, 3]
}
```

### GET /api/salary/debts

Список долгов сотрудников.

**Параметры запроса:**
- `role` (master|manager, optional)
- `status` (active|inactive, optional)

**Ответ:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "employee_id": 2,
        "employee_name": "Петр",
        "role": "master",
        "accrued_cents": 50000,
        "bonuses_cents": 0,
        "fines_cents": 10000,
        "paid_cents": 0,
        "owed_cents": 40000
      }
    ],
    "totals": {
      "total_to_pay_cents": 40000,
      "total_debt_company_cents": 0
    }
  }
}
```

### GET /reports/salary-debts

Отчет по долгам сотрудников.

**Ответ:** HTML страница

## Rate Limiting

Система использует Flask-Limiter для защиты от злоупотреблений и brute-force атак.

### Ограничения по умолчанию

- **Общие запросы:** 200 запросов в день, 1000 запросов в час
- **Критичные endpoints:**
  - `/login`: 5 попыток в минуту
  - `/api/statuses`: 100 запросов в час
  - `/api/parts`: 200 запросов в час

### Заголовки ответа

При превышении лимита возвращается HTTP 429 (Too Many Requests) с заголовками:
- `X-RateLimit-Limit` - максимальное количество запросов
- `X-RateLimit-Remaining` - оставшееся количество запросов
- `X-RateLimit-Reset` - время сброса лимита (Unix timestamp)

### Пример ответа при превышении лимита

```json
{
  "error": "429 Too Many Requests: Rate limit exceeded"
}
```

## Rate Limiting (Legacy)

API endpoints защищены от злоупотреблений через Flask-Limiter:

### Лимиты по endpoints

- **По умолчанию:** `200 запросов в день, 1000 в час`
- **`/login`:** `5 попыток в минуту` (защита от brute-force)
- **`/api/statuses`:** `100 запросов в час`
- **`/api/parts`:** `200 запросов в час`

### Обработка превышения лимита

При превышении лимита возвращается:
- **HTTP статус:** `429 Too Many Requests`
- **Заголовок:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Тело ответа:**
```json
{
  "error": "429 Too Many Requests: Rate limit exceeded"
}
```

### Рекомендации

- Используйте кэширование на стороне клиента для часто запрашиваемых данных
- Реализуйте экспоненциальную задержку при получении 429 ошибки
- Для массовых операций используйте batch endpoints (если доступны)

## CSRF Protection

Все POST/PUT/DELETE запросы защищены от CSRF атак через Flask-WTF.

### Использование в формах

Для HTML форм необходимо включать CSRF токен:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

### Использование в AJAX запросах

Для AJAX запросов токен передается в заголовке:
```javascript
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrf_token'),
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```

### Исключения

Некоторые API endpoints исключены из CSRF защиты (для интеграций):
- `POST /api/customers` - создание клиентов
- `GET /api/device/detail` - получение деталей устройства
- `PUT /api/customers/update` - обновление клиента
- `DELETE /api/customers/delete` - удаление клиента
- `POST /api/customers/add-device` - добавление устройства к клиенту
- `PUT /api/order/<order_id>/status` - обновление статуса заявки
- Warehouse endpoints (операции со складом)

**Важно:** Эти endpoints все еще требуют аутентификации через Flask-Login.

**Внимание:** Исключенные endpoints должны быть защищены другими способами (IP whitelist, API ключи и т.д.)

## Примеры использования

### Создание заявки через API

```python
import requests

# Вход в систему
session = requests.Session()
session.post('http://127.0.0.1:5000/login', data={
    'username': 'admin',
    'password': 'password'
})

# Создание заявки
response = session.post('http://127.0.0.1:5000/add_order', data={
    'client_name': 'Иван Иванов',
    'phone': '+79991234567',
    'device_type': 1,
    'device_brand': 1,
    'manager': 1
})
```

### Добавление услуги к заявке

```python
import requests

response = requests.post(
    'http://127.0.0.1:5000/api/orders/1/services',
    json={
        'service_id': 1,
        'quantity': 1,
        'price': 1000.00
    },
    cookies=session.cookies
)

result = response.json()
if result['success']:
    print(f"Услуга добавлена, ID: {result['id']}")
```

### Получение списка заявок

```python
import requests

response = requests.get(
    'http://127.0.0.1:5000/all_orders',
    params={
        'status': 'new',
        'page': 1,
        'per_page': 50
    },
    cookies=session.cookies
)
```

## Версионирование

В настоящее время API не версионируется. При необходимости можно добавить префикс версии:

```
/api/v1/orders
/api/v2/orders
```

### Финансы (Finance)

#### GET /finance/cash

Страница кассы с операциями.

**Параметры запроса:**
- `period` (string, optional) - период (today, yesterday, week, month, last_month, year, custom)
- `date_from` (string, optional) - дата начала (YYYY-MM-DD)
- `date_to` (string, optional) - дата окончания (YYYY-MM-DD)

**В списке операций:**
- Ссылка «Заявка #N» ведёт на `/order/<order_uuid или order_id>`.
- Ссылка «Чек #N» (при наличии `payment_id`) ведёт на `/finance/payment/<payment_id>` (детали оплаты/чека).
- Ручные операции отображаются как «Операция #N» без ссылки.

**Ответ:** HTML страница с кассовыми операциями

#### GET /finance/categories

Страница управления статьями доходов/расходов.

**Ответ:** HTML страница со списком категорий

#### POST /finance/api/categories

Создание категории транзакций.

**Тело запроса (JSON):**
```json
{
  "name": "Аренда",
  "type": "expense",
  "description": "Аренда помещения"
}
```

**Ответ:**
```json
{
  "success": true,
  "id": 5
}
```

#### PUT /finance/api/categories/<category_id>

Обновление категории транзакций.

**Тело запроса (JSON):**
```json
{
  "name": "Аренда офиса",
  "description": "Обновленное описание"
}
```

#### DELETE /finance/api/categories/<category_id>

Удаление категории (только пользовательские).

**Ответ:**
```json
{
  "success": true
}
```

#### POST /finance/api/transactions

Создание кассовой операции.

**Тело запроса (JSON):**
```json
{
  "category_id": 5,
  "amount": 15000.00,
  "payment_method": "cash",
  "description": "Оплата аренды за январь"
}
```

**Ответ:**
```json
{
  "success": true,
  "id": 10
}
```

**Примечание:** Расходные операции могут привести к отрицательному балансу кассы.

#### DELETE /finance/api/transactions/<transaction_id>

Удаление кассовой операции.

**Ответ:**
```json
{
  "success": true
}
```

#### GET /finance/profit

Страница отчёта о прибыли.

**Параметры запроса:**
- `period` (string, optional) - период фильтрации
- `date_from` (string, optional) - дата начала
- `date_to` (string, optional) - дата окончания

**Ответ:** HTML страница с отчётом о прибыли

#### GET /finance/analytics

Страница финансовой аналитики.

**Параметры запроса:**
- `period` (string, optional) - период фильтрации
- `date_from` (string, optional) - дата начала
- `date_to` (string, optional) - дата окончания

**Ответ:** HTML страница с аналитикой

### Магазин (Shop)

#### GET /shop/

Главная страница магазина для быстрых продаж.

**Ответ:** HTML страница с формой продажи и списком последних продаж

#### GET /shop/sale/<sale_id>

Детали продажи.

**Параметры:**
- `sale_id` (int) - ID продажи

**Ответ:** HTML страница с деталями продажи (товары, услуги, себестоимость, прибыль)

#### GET /shop/api/customers/search

Поиск клиентов для выбора при продаже.

**Параметры запроса:**
- `q` (string, required) - поисковый запрос (минимум 2 символа)

**Пример:**
```
GET /shop/api/customers/search?q=Иван
```

**Ответ:**
```json
{
  "success": true,
  "customers": [
    {
      "id": 1,
      "name": "Иван Иванов",
      "phone": "+79991234567",
      "email": "ivan@example.com",
      "label": "Иван Иванов (+79991234567)"
    }
  ]
}
```

#### POST /shop/api/sales

Создание продажи.

**Тело запроса (JSON):**
```json
{
  "items": [
    {"type": "part", "id": 1, "quantity": 2, "price": 500.00},
    {"type": "service", "id": 3, "quantity": 1, "price": 1000.00}
  ],
  "payment_method": "cash",
  "customer_id": 1,
  "customer_name": "Иван Иванов",
  "customer_phone": "+79991234567",
  "notes": "Примечание к продаже"
}
```

**Ответ:**
```json
{
  "success": true,
  "sale_id": 5,
  "total": 2000.00
}
```

**Особенности:**
- Автоматическое списание товаров со склада
- Автоматическое создание записи в кассе (категория "Продажа товаров")
- Автоматическое создание записи в движениях склада
- Логирование операции в action_logs

#### GET /shop/api/search

Поиск товаров и услуг.

**Параметры запроса:**
- `q` (string, required) - поисковый запрос

**Пример:**
```
GET /shop/api/search?q=экран
```

**Ответ:**
```json
{
  "success": true,
  "results": [
    {
      "type": "part",
      "id": 1,
      "name": "Экран iPhone 12",
      "part_number": "SCR-IP12",
      "price": 5000.00,
      "stock_quantity": 10,
      "purchase_price": 3500.00
    },
    {
      "type": "service",
      "id": 5,
      "name": "Замена экрана",
      "price": 2000.00
    }
  ]
}
```

## Уведомления (Notifications)

### GET /api/notifications
Получает уведомления текущего пользователя.

**Параметры запроса:**
- `unread_only` (optional, default: 0) - Только непрочитанные (1/0)
- `limit` (optional, default: 50, max: 200) - Лимит записей

**Ответ:**
```json
{
  "success": true,
  "notifications": [
    {
      "id": 1,
      "type": "in_app",
      "title": "Новая задача",
      "message": "Вам назначена задача",
      "entity_type": "task",
      "entity_id": 5,
      "read_at": null,
      "created_at": "2026-01-26 10:00:00"
    }
  ]
}
```

### GET /api/notifications/unread-count
Получает количество непрочитанных уведомлений.

**Ответ:**
```json
{
  "success": true,
  "count": 5
}
```

### POST /api/notifications/<notification_id>/read
Отмечает уведомление как прочитанное.

**Ответ:**
```json
{
  "success": true
}
```

### POST /api/notifications/read-all
Отмечает все уведомления как прочитанные.

**Ответ:**
```json
{
  "success": true,
  "count": 10
}
```

### GET /api/notifications/preferences
Получает настройки уведомлений пользователя.

**Ответ:**
```json
{
  "success": true,
  "preferences": [
    {
      "notification_type": "order_status_change",
      "enabled": true,
      "email_enabled": true,
      "push_enabled": true
    }
  ]
}
```

### POST /api/notifications/preferences
Устанавливает настройки уведомлений.

**Тело запроса:**
```json
{
  "notification_type": "order_status_change",
  "enabled": true,
  "email_enabled": true,
  "push_enabled": false
}
```

**Ответ:**
```json
{
  "success": true
}
```

## Комментарии (Comments)

### POST /api/comments/upload
Загружает файл для комментария.

**Форма:**
- `file` (required) - Файл для загрузки

**Ответ:**
```json
{
  "success": true,
  "attachment_id": 1,
  "filename": "screenshot.png",
  "file_path": "/uploads/comments/1/screenshot.png"
}
```

### GET /api/comments/attachment/<attachment_id>
Получает файл вложения комментария.

**Ответ:** Файл (binary)

## Задачи (Tasks)

### GET /api/tasks
Получает задачи пользователя.

**Параметры запроса:**
- `order_id` (optional) - Фильтр по заявке
- `status` (optional) - Фильтр по статусу (todo, in_progress, done, cancelled)
- `assigned_to` (optional) - Фильтр по исполнителю

**Ответ:**
```json
{
  "success": true,
  "tasks": [
    {
      "id": 1,
      "order_id": 123,
      "title": "Проверить устройство",
      "description": "Проверить работоспособность",
      "assigned_to": 5,
      "deadline": "2026-01-27",
      "priority": "high",
      "status": "todo",
      "checklist": [
        {
          "id": 1,
          "item_text": "Проверить экран",
          "is_completed": false
        }
      ]
    }
  ]
}
```

### POST /api/tasks
Создает новую задачу.

**Тело запроса:**
```json
{
  "order_id": 123,
  "title": "Проверить устройство",
  "description": "Проверить работоспособность",
  "assigned_to": 5,
  "deadline": "2026-01-27",
  "priority": "high",
  "checklist": [
    {"item_text": "Проверить экран"},
    {"item_text": "Проверить кнопки"}
  ]
}
```

**Ответ:**
```json
{
  "success": true,
  "task_id": 1
}
```

### GET /api/tasks/<task_id>
Получает задачу по ID.

**Ответ:**
```json
{
  "success": true,
  "task": {
    "id": 1,
    "order_id": 123,
    "title": "Проверить устройство",
    "status": "todo",
    "checklist": []
  }
}
```

### PUT /api/tasks/<task_id>
Обновляет задачу.

**Тело запроса:**
```json
{
  "title": "Обновленное название",
  "status": "in_progress"
}
```

**Ответ:**
```json
{
  "success": true
}
```

### DELETE /api/tasks/<task_id>
Удаляет задачу.

**Ответ:**
```json
{
  "success": true
}
```

### GET /api/tasks/overdue
Получает просроченные задачи.

**Ответ:**
```json
{
  "success": true,
  "tasks": []
}
```

## Шаблоны заявок (Templates)

### GET /api/templates
Получает список шаблонов заявок.

**Параметры запроса:**
- `is_public` (optional) - Только публичные (1/0)

**Ответ:**
```json
{
  "success": true,
  "templates": [
    {
      "id": 1,
      "name": "Ремонт телефона",
      "description": "Стандартный шаблон",
      "template_data": {
        "device_type_id": 1,
        "services": [1, 2],
        "default_status": 1
      },
      "is_public": true
    }
  ]
}
```

### POST /api/templates
Создает новый шаблон.

**Тело запроса:**
```json
{
  "name": "Ремонт телефона",
  "description": "Стандартный шаблон",
  "template_data": {
    "device_type_id": 1,
    "services": [1, 2],
    "default_status": 1
  },
  "is_public": true
}
```

**Ответ:**
```json
{
  "success": true,
  "template_id": 1
}
```

### GET /api/templates/<template_id>
Получает шаблон по ID.

**Ответ:**
```json
{
  "success": true,
  "template": {
    "id": 1,
    "name": "Ремонт телефона",
    "template_data": {}
  }
}
```

### PUT /api/templates/<template_id>
Обновляет шаблон.

**Тело запроса:**
```json
{
  "name": "Обновленное название",
  "template_data": {}
}
```

**Ответ:**
```json
{
  "success": true
}
```

### DELETE /api/templates/<template_id>
Удаляет шаблон.

**Ответ:**
```json
{
  "success": true
}
```


**Ответ:**
```json
{
  "success": true,
  "data": [
    {
      "status": "Новая",
      "count": 50
    },
    {
      "status": "В работе",
      "count": 30
    }
  ]
}
```

## Поиск (Search)

### GET /search
Страница результатов поиска (HTML).

**Параметры запроса:**
- `q` (required) - Поисковый запрос
- `type` (optional, multiple) - Фильтр по типу (orders, customers, parts)

### GET /api/search
Получает результаты поиска.

**Параметры запроса:**
- `q` (required) - Поисковый запрос
- `type` (optional, multiple) - Фильтр по типу
- `limit` (optional, default: 50) - Лимит результатов

**Ответ:**
```json
{
  "success": true,
  "results": {
    "orders": [
      {
        "id": 123,
        "client_name": "Иван Иванов",
        "phone": "+79991234567"
      }
    ],
    "customers": [],
    "parts": []
  }
}
```

### GET /api/autocomplete
Получает автодополнение для поиска.

**Параметры запроса:**
- `q` (required) - Поисковый запрос
- `limit` (optional, default: 10) - Лимит результатов

**Ответ:**
```json
{
  "success": true,
  "suggestions": [
    {
      "type": "order",
      "id": 123,
      "text": "Заявка #123 - Иван Иванов"
    }
  ]
}
```

## Публичный портал клиента (Customer Portal)

### Автоматическая генерация пароля

При создании нового клиента система автоматически генерирует пароль для доступа к порталу:
- Пароль состоит из 8 символов (буквы и цифры)
- Пароль сохраняется в зашифрованном виде в базе данных
- При первом входе клиент обязан сменить пароль

### GET /portal/login
Страница входа в портал (HTML, публичная).

**Особенности:**
- При первом входе автоматически показывается форма смены пароля
- Форма защищена CSRF токеном

### POST /portal/login
Вход в портал.

**Форма:**
- `phone` (required) - Телефон клиента
- `password` (required) - Текущий пароль портала
- `new_password` (optional) - Новый пароль (требуется при первом входе)
- `new_password_confirm` (optional) - Подтверждение нового пароля
- `change_password` (optional) - Флаг смены пароля (true/false)

**Ответ:** 
- При успешном входе: редирект на `/portal/dashboard`
- При первом входе: форма смены пароля
- При ошибке: страница входа с сообщением об ошибке

### POST /portal/logout
Выход из портала.

**Ответ:** Редирект на `/portal/login`

### GET /portal/dashboard
Дашборд клиента (HTML, требует авторизацию в портале).

### GET /portal/orders
История заявок клиента (HTML).

### GET /portal/payments
История платежей клиента (HTML).

### GET /portal/wallet
Баланс кошелька клиента (HTML).

### POST /api/customers/<id>/portal-password
Устанавливает пароль портала для клиента (только для авторизованных пользователей CRM с правом `edit_customers`).

**Тело запроса:**
```json
{
  "password": "новый_пароль"
}
```

**Ответ:**
```json
{
  "success": true,
  "message": "Пароль портала установлен"
}
```

**Ошибки:**
- `400` - Пароль обязателен или слишком короткий (минимум 4 символа)
- `401` - Требуется авторизация
- `403` - Нет прав на редактирование клиентов
- `500` - Внутренняя ошибка сервера

### DELETE /api/customers/<id>/portal-password
Удаляет пароль портала для клиента (отключает доступ к порталу).

**Ответ:**
```json
{
  "success": true,
  "message": "Пароль портала удален"
}
```

## Документация OpenAPI/Swagger

В будущем планируется добавление документации OpenAPI/Swagger для автоматической генерации клиентов и интерактивной документации.

## Последние изменения (2026-01-26)

### 🚀 Новые API endpoints

#### Уведомления
- `GET /api/notifications` - получение уведомлений
- `GET /api/notifications/unread-count` - количество непрочитанных
- `POST /api/notifications/<id>/read` - отметить как прочитанное
- `POST /api/notifications/read-all` - отметить все как прочитанные
- `GET /api/notifications/preferences` - настройки уведомлений
- `POST /api/notifications/preferences` - установка настроек

#### Комментарии
- `POST /api/comments/upload` - загрузка файла
- `GET /api/comments/attachment/<id>` - получение файла

#### Задачи
- `GET /api/tasks` - список задач
- `POST /api/tasks` - создание задачи
- `GET /api/tasks/<id>` - получение задачи
- `PUT /api/tasks/<id>` - обновление задачи
- `DELETE /api/tasks/<id>` - удаление задачи
- `GET /api/tasks/overdue` - просроченные задачи

#### Шаблоны
- `GET /api/templates` - список шаблонов
- `POST /api/templates` - создание шаблона
- `GET /api/templates/<id>` - получение шаблона
- `PUT /api/templates/<id>` - обновление шаблона
- `DELETE /api/templates/<id>` - удаление шаблона

#### Поиск
- `GET /search` - страница результатов
- `GET /api/search` - результаты поиска
- `GET /api/autocomplete` - автодополнение

#### Публичный портал
- `GET /portal/login` - вход в портал
- `POST /portal/login` - аутентификация
- `POST /portal/logout` - выход
- `GET /portal/dashboard` - дашборд клиента
- `GET /portal/orders` - заявки клиента
- `GET /portal/payments` - платежи клиента
- `GET /portal/wallet` - кошелёк клиента
- `POST /api/customers/<id>/portal-password` - установка пароля портала
- `DELETE /api/customers/<id>/portal-password` - удаление пароля портала

### Изменения в существующих endpoints

#### POST /api/order/<order_id>/comment
**Добавлено:**
- `is_internal` (optional) - внутренний комментарий
- `attachment_ids` (optional) - массив ID вложений

**Пример:**
```json
{
  "comment": "Комментарий @admin",
  "is_internal": false,
  "attachment_ids": [1, 2]
}
```

## Последние изменения (2026-01-18)

### Исправления безопасности
- ✅ Все 61 API endpoint защищены аутентификацией
- ✅ Исправлена ошибка добавления платежей для закрытых заявок
- ✅ Убраны повторные импорты, вызывающие ошибки

### Новые возможности
- ✅ Разрешено добавление платежей для закрытых заявок (при закрытии заявки)
- ✅ Улучшена обработка ошибок валидации
- ✅ Добавлено логирование просмотра заявок

### Изменения в API

#### POST /api/orders/<order_id>/payments
**Изменение:** Теперь разрешено добавлять платежи даже для закрытых заявок. Это необходимо для случая, когда при закрытии заявки нужно добавить платеж.

**Было:** Проверка `check_order_edit_allowed` блокировала добавление платежей для закрытых заявок.

**Стало:** Проверяется только существование заявки. Платежи можно добавлять для всех статусов.

---

## Последние изменения (2026-02-23)

### Настройки и шаблоны писем

- В `general_settings` больше не используются поля:
  - `portal_public_url`
  - `review_url`
  - `director_contact_url`
- Ссылки для клиентских писем задаются напрямую в email-шаблонах.

### Статусы в /all_orders

- Для реестра `/all_orders?view=registry` выпадающий список быстрой смены статуса возвращает только активные статусы (`is_archived = 0`).

### Зарплата и отчеты

- При обычной смене статуса начисление зарплаты выполняется только если по заявке еще нет начислений.
- Повторный сценарий `Закрыт -> другой статус -> Закрыт` не создает новые начисления.
- Добавлена защита на уровне БД: уникальный индекс `ux_salary_accruals_business_key` (миграция `053`).

Подробно: [RELEASE_NOTES_2026-02-23.md](RELEASE_NOTES_2026-02-23.md)

---

**Версия документа:** 2.1  
**Последнее обновление:** 2026-02-23

