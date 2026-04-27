# Routes (Маршруты)

Маршруты обрабатывают HTTP запросы и возвращают HTML страницы или JSON ответы.

## Архитектура

Маршруты организованы в Blueprint'ы Flask:
- Каждый модуль имеет свой Blueprint
- Все Blueprint'ы регистрируются в `app/__init__.py`
- Используются декораторы для аутентификации и авторизации

## Структура

Все маршруты находятся в пакете `app.routes`:

```
app/routes/
├── main.py          # Главная страница, логин, настройки
├── orders.py        # Заявки
├── customers.py     # Клиенты
├── warehouse.py     # Склад
├── finance.py       # Финансы
├── shop.py          # Магазин (быстрые продажи)
├── reports.py       # Отчеты
├── settings.py      # Настройки
├── statuses.py      # Статусы заявок
├── salary.py        # Зарплата
├── staff_chat.py    # Чат сотрудников (REST + Socket.IO namespace /staff-chat)
└── api.py           # Общие API endpoints
```

## Декораторы

### @login_required
Требует аутентификации пользователя:

```python
from flask_login import login_required

@bp.route('/orders')
@login_required
def orders():
    return render_template('orders.html')
```

### @role_required('admin')
Требует определенной роли:

```python
from app.routes.main import role_required

@bp.route('/admin')
@login_required
@role_required('admin')
def admin_page():
    return render_template('admin.html')
```

### @permission_required('permission_name')
Требует конкретного права доступа:

```python
from app.routes.main import permission_required

@bp.route('/warehouse')
@login_required
@permission_required('manage_warehouse')
def warehouse():
    return render_template('warehouse.html')
```

## Основные Blueprint'ы

### main (app/routes/main.py)
- `/` - главная страница (дашборд владельца: финансы/CRM/склад, единый период)
- `/login` - вход в систему
- `/logout` - выход
- `/settings` - настройки системы
- `/api/settings/*` - API для настроек

### orders (app/routes/orders.py)
- `/all_orders` - список заявок
- `/add_order` - создание заявки
- `/order/<uuid>` - детали заявки
- `/api/orders/*` - API для заявок

### customers (app/routes/customers.py)
- `/clients` - список клиентов
- `/client/<id>` - детали клиента
- `/api/customers/*` - API для клиентов

### warehouse (app/routes/warehouse.py)
- `/warehouse` - товары на складе
- `/warehouse/purchases` - закупки
- `/warehouse/movements` - движения товаров
- `/warehouse/logs` - история операций

### finance (app/routes/finance.py)
- `/finance/cash` - касса
- `/finance/profit` - прибыль
- `/finance/analytics` - аналитика
- `/finance/api/*` - API для финансов

### shop (app/routes/shop.py)
- `/shop` - быстрые продажи
- `/shop/sale/<id>` - детали продажи
- `/shop/api/*` - API для магазина

### staff_chat (app/routes/staff_chat.py)
- `/api/staff-chat/*` — история, отправка, вложения, реакции, курсор прочитанного, читатели, Web Push subscribe/unsubscribe
- Регистрация обработчиков Socket.IO: `init_staff_chat_socketio(socketio)` в `app/__init__.py`
- См. [docs/API.md](../../docs/API.md) — раздел «Чат сотрудников»

### reports (app/routes/reports.py)
- `/reports/dashboard` - сводный отчет по компании
- `/reports/summary` - legacy URL (redirect на `/reports/dashboard`)
- `/reports/sales` - отчет по продажам
- `/reports/cash` - отчет по кассе
- `/reports/api/dashboard` - API дашборда

## API Endpoints

Все API endpoints требуют аутентификации (`@login_required`).

### Orders API
- `GET/POST /api/datatables/orders` - список заявок (DataTables; в UI — POST)
- `POST /api/orders/check_duplicate` - проверка дубликатов
- `PUT /api/order/<id>/status` - изменение статуса
- `POST /api/orders/<id>/payments` - добавление оплаты
- `GET /api/orders/<id>/services` - услуги заявки
- `POST /api/orders/<id>/services` - добавление услуги

### Customers API
- `GET /api/datatables/clients` - список клиентов
- `POST /api/customers` - создание клиента
- `GET /api/customers/<id>` - детали клиента
- `PUT /api/customers/<id>` - обновление клиента

### Warehouse API
- `POST /api/warehouse/adjust-stock` - корректировка остатков

### Finance API
- `GET /finance/api/categories` - категории транзакций
- `POST /finance/api/transactions` - создание операции
- `DELETE /finance/api/transactions/<id>` - удаление операции

### Staff Chat API
- `GET /api/staff-chat/history`, `POST /api/staff-chat/send`, `POST /api/staff-chat/upload`, и др. — см. [docs/API.md](../../docs/API.md)

Подробнее: [docs/API.md](../../docs/API.md)

## Формат ответов

### HTML ответы
```python
return render_template('orders.html', orders=orders)
```

### JSON ответы
```python
return jsonify({
    'success': True,
    'data': {...}
})
```

### Ошибки
```python
return jsonify({
    'success': False,
    'error': 'Сообщение об ошибке'
}), 400
```

Подробнее: [docs/development/ROUTES.md](../../docs/development/ROUTES.md)

## Актуализация (2026-04-10)

- Добавлен blueprint **staff_chat**: внутренний чат, Web Push (VAPID), курсоры прочитанного. Подробно: [docs/API.md](../../docs/API.md), [docs/USER_GUIDE.md](../../docs/USER_GUIDE.md).

## Актуализация (2026-02-23)

- В server-side DataTables источнике `/all_orders` список статусов для quick dropdown ограничен только активными статусами (`is_archived = 0`).
- В цепочке смены статуса добавлена защита от повторного начисления зарплаты при повторном входе в закрывающий статус.
- Логика уведомлений и поведения `/settings` синхронизирована с шаблонами писем и директорскими уведомлениями.

Подробно: [docs/RELEASE_NOTES_2026-02-23.md](../../docs/RELEASE_NOTES_2026-02-23.md)
