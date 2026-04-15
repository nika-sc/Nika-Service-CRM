# Services (Сервисы)

Сервисы содержат бизнес-логику приложения и обеспечивают слой абстракции между маршрутами (routes) и моделями/запросами (models/queries).

## Архитектура

Сервисы следуют паттерну Service Layer и обеспечивают:
- Инкапсуляцию бизнес-логики
- Валидацию данных
- Обработку ошибок
- Кэширование результатов
- Транзакционность операций

## Структура

Все сервисы находятся в пакете `app.services` и экспортируются через `__init__.py`:

```python
from app.services import OrderService, CustomerService, DeviceService
```

## Список сервисов

### OrderService
Сервис для работы с заявками.

**Основные методы:**
- `get_order(order_id)` - получение заявки по ID
- `get_order_by_uuid(order_uuid)` - получение заявки по UUID
- `get_orders_with_details(filters, page, per_page)` - список заявок с фильтрацией
- `create_order(**data)` - создание новой заявки
- `update_order(order_id, **data)` - обновление заявки
- `update_order_status(order_id, status_id)` - изменение статуса
- `add_order_service(order_id, service_id, quantity, price)` - добавление услуги
- `add_order_part(order_id, part_id, quantity, price)` - добавление запчасти
- `check_order_edit_allowed(order_id)` - проверка разрешения редактирования

### CustomerService
Сервис для работы с клиентами.

**Основные методы:**
- `get_customer(customer_id)` - получение клиента
- `get_customer_by_phone(phone)` - поиск по телефону
- `create_customer(**data)` - создание клиента
- `update_customer(customer_id, **data)` - обновление клиента
- `search_customers(query)` - поиск клиентов

### DeviceService
Сервис для работы с устройствами.

**Основные методы:**
- `get_device(device_id)` - получение устройства
- `create_device(customer_id, **data)` - создание устройства
- `update_device(device_id, **data)` - обновление устройства
- `get_customer_devices(customer_id)` - устройства клиента

### PaymentService
Сервис для работы с оплатами.

**Основные методы:**
- `add_payment(order_id, amount, payment_type, ...)` - добавление оплаты
- `cancel_payment(payment_id, reason)` - отмена оплаты
- `refund_payment(payment_id, amount)` - возврат оплаты
- `get_order_payments(order_id)` - оплаты заявки

### WalletService
Сервис для работы с кошельком клиента (депозитом).

**Основные методы:**
- `get_balance(customer_id)` - баланс кошелька
- `credit(customer_id, amount, ...)` - пополнение кошелька
- `debit(customer_id, amount, ...)` - списание с кошелька
- `get_transactions(customer_id)` - история операций

### WarehouseService
Сервис для работы со складом.

**Основные методы:**
- `get_stock_levels(...)` - остатки товаров
- `create_part(**data)` - создание товара
- `add_part_income(part_id, quantity, ...)` - приход товара
- `add_part_expense(part_id, quantity, ...)` - списание товара
- `record_sale(part_id, quantity, order_id)` - продажа товара
- `record_return(part_id, quantity, order_id)` - возврат товара
- `get_categories()` - категории товаров

### FinanceService
Сервис для финансового модуля.

**Основные методы:**
- `get_transaction_categories(...)` - категории транзакций
- `create_transaction(...)` - создание кассовой операции
- `get_transactions(...)` - список операций
- `get_cash_summary(...)` - сводка по кассе
- `get_profit_report(...)` - отчет о прибыли
 - `transfer_between_methods(amount, from_method, to_method, ...)` - внутренний перевод между способами оплаты (Наличные ↔ Перевод и др.): создаёт пару операций расход/приход, не влияющих на «Приход/Расход за период», но изменяющих остатки по способам оплаты

### ReportsService
Сервис для генерации отчетов.

**Основные методы:**
- `get_stock_report(...)` - отчет по остаткам
- `get_sales_report(...)` - отчет по продажам
- `get_profitability_report(...)` - отчет по маржинальности
- `get_cash_report(...)` - отчет по кассе

### DashboardService
Сервис для сводных дашбордов (главная страница и `/reports/dashboard`).

**Основные методы:**
- `get_full_dashboard(...)` - полный набор KPI для владельца
- `get_company_summary(...)` - выручка/услуги/товары/магазин
- `get_cashflow_summary(...)` - поступления/расходы и разрез по оплатам
- `get_receivables_summary(...)` - дебиторка по активным заявкам
- `get_customers_kpis(...)` - новые/активные/возвращающиеся клиенты
- `get_warehouse_kpis(...)` - оценка склада, low-stock, закупки

### UserService
Сервис для работы с пользователями.

**Основные методы:**
- `create_user(username, password, role)` - создание пользователя
- `get_user_by_username(username)` - получение по логину
- `verify_password(password, password_hash)` - проверка пароля
- `check_role_permission(user_role, required_role)` - проверка прав
- `get_all_users(...)` - список пользователей

### SalaryService
Сервис для расчета зарплаты.

**Основные методы:**
- `calculate_order_profit(order_id)` - расчет прибыли по заявке
- `calculate_salary_for_order(order_id)` - расчет зарплаты
- `accrue_salary_for_order(order_id)` - начисление зарплаты
- `get_salary_report(...)` - отчет по зарплате

### StatusService
Сервис для работы со статусами заявок.

**Основные методы:**
- `get_all_statuses(...)` - все статусы
- `create_status(...)` - создание статуса
- `update_status(status_id, ...)` - обновление статуса

### ActionLogService
Сервис для логирования действий.

**Основные методы:**
- `log_action(...)` - логирование действия
- `get_action_logs(...)` - получение логов

### StaffChatService / StaffChatWebPushService
Внутренний чат сотрудников и доставка Web Push.

**StaffChatService** (`staff_chat_service.py`): история, создание сообщений и вложений, реакции, курсоры прочитанного (`upsert_read_cursor`), список читателей, лимиты отправки.

**StaffChatWebPushService** (`staff_chat_web_push_service.py`): сохранение подписок Push, рассылка при новом сообщении (фоновый поток, VAPID через `pywebpush`).

### ReferenceService
Сервис для работы со справочниками.

**Основные методы:**
- `get_device_types()` - типы устройств
- `get_device_brands()` - бренды устройств
- `get_order_statuses()` - статусы заявок
- `get_services()` - услуги
- `get_parts(...)` - товары

### BackupService
Сервис для резервного копирования БД.

**Основные методы:**
- `create_backup(...)` - создание бэкапа
- `restore_backup(backup_path)` - восстановление
- `get_backup_list(...)` - список бэкапов

## Использование

```python
from app.services import OrderService, CustomerService

# Создание заявки
order = OrderService.create_order(
    customer_name='Иван Иванов',
    phone='+79991234567',
    device_type_id=1,
    manager_id=1
)

# Поиск клиента
customer = CustomerService.get_customer_by_phone('+79991234567')
```

## Обработка ошибок

Все сервисы используют декоратор `@handle_service_error` для единообразной обработки ошибок:

- `ValidationError` - ошибки валидации данных
- `NotFoundError` - ресурс не найден
- `DatabaseError` - ошибки базы данных

Подробнее: [docs/development/SERVICES.md](../../docs/development/SERVICES.md)

## Актуализация (2026-04-10)

- Добавлены **StaffChatService** и **StaffChatWebPushService** — см. [docs/API.md](../../docs/API.md) (чат сотрудников).

## Актуализация (2026-02-23)

- `NotificationService`: убраны зависимости от отдельных ссылочных настроек (`portal_public_url/review_url/director_contact_url`), фокус на HTML-шаблоны писем.
- `OrderService.update_order_status`: начисление зарплаты при смене статуса выполняется только при отсутствии начислений, чтобы исключить дубли при повторном закрытии.
- `SettingsService`: удалены устаревшие ссылочные поля из текущей логики сохранения `general_settings`.
- `WarehouseService`/уведомления: канал `low_stock` работает через общую систему типов уведомлений и права пользователей.

Подробно: [docs/RELEASE_NOTES_2026-02-23.md](../../docs/RELEASE_NOTES_2026-02-23.md)
