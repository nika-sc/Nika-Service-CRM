# Queries (SQL Запросы)

Query классы содержат оптимизированные SQL запросы для работы с базой данных.

## Архитектура

Query классы обеспечивают:
- Оптимизацию SQL запросов
- Избежание N+1 проблем через JOIN
- Переиспользование запросов
- Типизацию результатов

## Структура

Все Query классы находятся в пакете `app.database.queries`:

```
app/database/queries/
├── order_queries.py        # Запросы для заявок
├── customer_queries.py     # Запросы для клиентов
├── device_queries.py        # Запросы для устройств
├── payment_queries.py      # Запросы для оплат
├── warehouse_queries.py    # Запросы для склада
├── reference_queries.py    # Запросы для справочников
├── status_queries.py       # Запросы для статусов
├── wallet_queries.py       # Запросы для кошелька
└── salary_queries.py       # Запросы для зарплаты
```

## Основные Query классы

### OrderQueries
Запросы для работы с заявками.

**Основные методы:**
- `get_orders_with_details(filters, page, per_page)` - список заявок с JOIN
- `get_order_full_data(order_id)` - полные данные заявки
- `get_order_status_history(order_id)` - история статусов
- `get_order_totals(order_id)` - итоги по заявке

### CustomerQueries
Запросы для работы с клиентами.

**Основные методы:**
- `search_customers(query, page, per_page)` - поиск клиентов
- `get_customer_orders(customer_id)` - заявки клиента
- `get_customer_devices(customer_id)` - устройства клиента

### PaymentQueries
Запросы для работы с оплатами.

**Основные методы:**
- `get_order_payments(order_id)` - оплаты заявки
- `get_payment_totals(order_id)` - итоги по оплатам
- `get_payments_by_period(date_from, date_to)` - оплаты за период

### WarehouseQueries
Запросы для работы со складом.

**Основные методы:**
- `get_stock_levels(...)` - остатки товаров
- `get_stock_movements(part_id, ...)` - движения товаров
- `get_categories()` - категории товаров
- `get_parts(search_query, category, ...)` - товары

### ReferenceQueries
Запросы для справочников.

**Основные методы:**
- `get_device_types()` - типы устройств
- `get_device_brands()` - бренды устройств
- `get_order_statuses()` - статусы заявок
- `get_services()` - услуги
- `get_order_models()` - модели устройств

### StatusQueries
Запросы для статусов заявок.

**Основные методы:**
- `get_all_statuses(include_archived)` - все статусы
- `get_status_by_id(status_id)` - статус по ID
- `get_status_by_code(code)` - статус по коду

### WalletQueries
Запросы для кошелька клиента.

**Основные методы:**
- `get_balance(customer_id)` - баланс кошелька
- `get_transactions(customer_id, limit)` - история операций
- `get_transaction_by_id(transaction_id)` - операция по ID

### SalaryQueries
Запросы для расчета зарплаты.

**Основные методы:**
- `get_salary_accruals(...)` - начисления зарплаты
- `get_salary_report(...)` - отчет по зарплате

## Использование

```python
from app.database.queries.order_queries import OrderQueries
from app.database.queries.customer_queries import CustomerQueries

# Получение заявок с фильтрацией
filters = {'status': 'new', 'customer_id': 1}
orders = OrderQueries.get_orders_with_details(filters, page=1, per_page=50)

# Поиск клиентов
customers = CustomerQueries.search_customers('Иван', page=1, per_page=20)
```

## Оптимизация

Query классы используют:
- **JOIN вместо множественных запросов** - избежание N+1 проблем
- **Индексы БД** - для быстрого поиска
- **Пагинация** - для больших списков
- **Кэширование** - для часто используемых данных

## Примеры оптимизированных запросов

### Избежание N+1 проблемы

**Плохо:**
```python
orders = get_orders()  # 1 запрос
for order in orders:
    customer = get_customer(order.customer_id)  # N запросов
```

**Хорошо:**
```python
orders = OrderQueries.get_orders_with_details()  # 1 запрос с JOIN
# customer уже включен в результат
```

Подробнее: [docs/development/DATABASE_QUERIES.md](../../docs/development/DATABASE_QUERIES.md)

## Актуализация (2026-02-23)

- Для `salary_accruals` введена защита от дублей на уровне БД (уникальный бизнес-индекс, миграция `053`).
- Исторические дубли по `salary_accruals` очищаются отдельным скриптом `scripts/dedupe_salary_accruals.py`.
- Отчеты `/salary` и `/reports/salary` читают фактические данные из `salary_accruals`; консистентность теперь дополнительно гарантируется индексом.

Подробно: [docs/RELEASE_NOTES_2026-02-23.md](../../docs/RELEASE_NOTES_2026-02-23.md)
