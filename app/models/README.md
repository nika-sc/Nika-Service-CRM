# Models (Модели)

Модели представляют бизнес-сущности и обеспечивают работу с данными на уровне объектов.

## Архитектура

Модели используют паттерн Active Record:
- Каждая модель соответствует таблице в БД
- Методы модели работают с конкретной записью
- Статические методы работают с коллекциями

## Структура

Все модели находятся в пакете `app.models`:

```
app/models/
├── base.py          # Базовый класс BaseModel
├── order.py         # Модель заявки
├── customer.py      # Модель клиента
├── device.py        # Модель устройства
├── part.py          # Модель товара
├── payment.py       # Модель оплаты
├── service.py       # Модель услуги
└── user.py          # Модель пользователя
```

## Базовый класс

Все модели наследуются от `BaseModel`:

```python
from app.models.base import BaseModel

class Order(BaseModel):
    table_name = 'orders'
    # ...
```

## Основные модели

### Order (app/models/order.py)
Модель заявки на ремонт.

**Основные методы:**
- `get_by_id(order_id)` - получение по ID
- `get_by_uuid(order_uuid)` - получение по UUID
- `create(**data)` - создание заявки
- `update(**data)` - обновление заявки
- `delete()` - удаление заявки

**Атрибуты:**
- `id` - ID заявки
- `order_id` - UUID заявки
- `customer_id` - ID клиента
- `device_id` - ID устройства
- `status_id` - ID статуса
- `manager_id` - ID менеджера
- `master_id` - ID мастера

### Customer (app/models/customer.py)
Модель клиента.

**Основные методы:**
- `get_by_id(customer_id)` - получение по ID
- `get_by_phone(phone)` - поиск по телефону
- `create(**data)` - создание клиента
- `update(**data)` - обновление клиента

**Атрибуты:**
- `id` - ID клиента
- `name` - имя клиента
- `phone` - телефон
- `email` - email
- `wallet_cents` - баланс кошелька (в копейках)

### Device (app/models/device.py)
Модель устройства.

**Основные методы:**
- `get_by_id(device_id)` - получение по ID
- `get_by_customer(customer_id)` - устройства клиента
- `create(**data)` - создание устройства
- `update(**data)` - обновление устройства

**Атрибуты:**
- `id` - ID устройства
- `customer_id` - ID клиента
- `device_type_id` - ID типа устройства
- `device_brand_id` - ID бренда
- `model` - модель устройства

### Part (app/models/part.py)
Модель товара на складе.

**Основные методы:**
- `get_by_id(part_id)` - получение по ID
- `get_all(category)` - все товары
- `create(**data)` - создание товара
- `update(**data)` - обновление товара

**Атрибуты:**
- `id` - ID товара
- `name` - название
- `part_number` - артикул
- `stock_quantity` - остаток
- `price` / `retail_price` - розничная цена (в зависимости от версии БД)
- `purchase_price` - закупочная цена

### Payment (app/models/payment.py)
Модель оплаты.

**Основные методы:**
- `get_by_id(payment_id)` - получение по ID
- `get_by_order(order_id)` - оплаты заявки
- `create(**data)` - создание оплаты

**Атрибуты:**
- `id` - ID оплаты
- `order_id` - ID заявки
- `amount` - сумма
- `payment_type` - тип оплаты (cash, card, transfer, wallet)
- `kind` - вид (payment, deposit, refund)
- `status` - статус (pending, captured, cancelled, refunded)

### User (app/models/user.py)
Модель пользователя.

**Основные методы:**
- `get_by_id(user_id)` - получение по ID
- `get_by_username(username)` - поиск по логину
- `create(**data)` - создание пользователя

**Атрибуты:**
- `id` - ID пользователя
- `username` - логин
- `password_hash` - хеш пароля
- `role` - роль (viewer, master, manager, admin)
- `is_active` - активен ли пользователь

## Использование

```python
from app.models.order import Order
from app.models.customer import Customer

# Получение заявки
order = Order.get_by_id(1)

# Создание клиента
customer = Customer.create(
    name='Иван Иванов',
    phone='+79991234567'
)

# Обновление заявки
order.update(status_id=2)
```

## Связи между моделями

- `Order` → `Customer` (через `customer_id`)
- `Order` → `Device` (через `device_id`)
- `Device` → `Customer` (через `customer_id`)
- `Payment` → `Order` (через `order_id`)

Подробнее: [docs/development/MODELS.md](../../docs/development/MODELS.md)
