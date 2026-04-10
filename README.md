# CRM System - Service Center

 <br>Система управления сервисным центром для работы с заявками, клиентами, устройствами и складом, полностью написана с помощью Cursor AI.
 <br>Созданная для работы в реальном сервисном центре, протестирована и в данны момент работает в моем сервисном центре Ника в Сочи.
  <br>Публикую для публичного доступа в помощь всем сервисным центрам, из за ограничений связи многие сталкнулись с проблемой доступа к SAAS платформам для сервинсых центров, по этой причине я создал свою CRM 
  <br>систему и внедрил в неё весь опыт и потребности своего сервисного центра в учете заявок и клиентов.
 <br>
 <br>Моя система позволяет работать без привязки к домену, интернету, может работать локально в вашей сети, либо утсановлена на VPS с вашим доменом.
  <br>Если вы заметили баг, или у вас есть предложения по функционалу то пишите на Email: nika-sc@bk.ru С пометкой "Nika-CRM"
 <br>Помощь по установке и интеграции в ваш сервис  Email: nika-sc@bk.ru 
  <br>С пометкой "Nika-CRM Помощь по установке."
 <br>Автор: Александр Смелков
 <br>Сервисный центр "Ника" 2026г г.Сочи
## Содержание

- [Описание и возможности](#описание)
- [Актуальные функции (быстрый обзор)](#актуальные-функции-быстрый-обзор)
- [Установка и конфигурация](#установка)
- [Архитектура](#архитектура)
- [Руководство пользователя](#руководство-пользователя)
- [API документация](#api-документация)
- [План скриптов](#план-скриптов-и-исправлений)
- [Маршруты и сервисы](#маршруты-и-сервисы)
- [Полный справочник системы](#полный-справочник-системы-по-результатам-сканирования-кода)
- [Безопасность и производительность](#безопасность)
- [История изменений](#история-изменений)

---

## Описание

Современная CRM система, построенная на Flask, с архитектурой, разделенной на слои:
- **Routes (Controllers)** - обработка HTTP запросов
- **Services** - бизнес-логика
- **Models** - модели данных
- **Queries** - оптимизированные SQL запросы
- **Database** - база данных PostgreSQL

## Возможности

## Актуальные функции (быстрый обзор)

Ниже перечислены ключевые функции, подтвержденные по текущей реализации проекта.

### Для клиентов
- **Личный кабинет клиента** (`/portal/*`): вход по телефону и паролю, отдельная клиентская сессия, ограничение запросов (rate limit), принудительная смена пароля при первом входе.
- **Разделы кабинета:** дашборд, заявки, платежи, устройства, кошелек клиента (переплаты/предоплаты).
- **Пароль портала клиента:** автоматическая генерация для нового клиента, ручная установка нового пароля, отключение доступа в портал.

### Для сотрудников
- **Внутренний чат сотрудников (real-time):** сообщения, редактирование/удаление, индикатор набора текста, вложения файлов.
- **Emoji и реакции в чате:** выбор эмодзи и реакции на сообщения с переключением (toggle) и агрегированным отображением.
- **Уведомления:** in-app уведомления, счетчик непрочитанных, отметка прочитанного, push через Socket.IO и email-канал.

### Операционная работа
- **Заявки и устройство:** реестр/канбан/журнал, расширенные фильтры и статусы, история устройства (`/device/<id>`).
- **Склад:** товары, категории, поставщики, закупки, инвентаризация, движения и журнал операций.
- **Финансы и касса:** приход/расход, категории, переводы между способами оплаты, карточки оплат и печать чеков.
- **Магазин быстрых продаж:** продажи без создания заявки с автоматической интеграцией со складом и кассой.

### Администрирование и надежность
- **RBAC (роли и права):** детальные права, управление пользователями и сотрудниками, кастомные роли `master_{id}` / `manager_{id}`.
- **Аудит действий:** журнал действий (`/action-logs`) с фильтрацией по типу, пользователю, периоду, объекту.
- **Шаблоны печати и системные настройки:** шаблоны документов и конфигурация системы в `/settings`.
- **Бэкапы и восстановление:** сервис резервного копирования + скрипты эксплуатации.

### Важно по текущим ограничениям
- API шаблонов заявок (`/api/templates/*`) в текущей версии отключен и возвращает `410 Gone`.
- Депозитные операции в заявках отключены (`410 Gone` для соответствующих endpoint'ов).

### Управление заявками
- Создание, редактирование, поиск и фильтрация заявок
- Реестр, Канбан и Журнал заявок
- **Реестр заявок** — расширенная таблица (21 колонка: суммы, даты, менеджер, долг и др.), скрытие/показ колонок с сохранением в браузере, перетаскивание колонок с сохранением порядка, верхняя горизонтальная прокрутка
- Статусы заявок (Новая, В работе, Готова, Закрыта)
- **Динамическая смена статуса** с цветными уведомлениями (в списке заявок и на странице заявки)
- **Флаги статусов**: окно оплаты, начисление зарплаты, финальный статус, запрет редактирования, гарантия, комментарий
- Поиск по клиенту, телефону, номеру заявки, модели устройства
- Фильтрация по статусу, менеджеру, мастеру, датам
- Сортировка по различным полям
- Поле "Модель" устройства с автопоиском (таблица `order_models`)
  - Доступно при создании и редактировании заявки
  - Автоматическое сохранение новых моделей в справочник
- Ссылки на историю устройства из таблицы заявок (поля "Устройство" и "Бренд")
- Отображение неисправностей и внешнего вида в виде тегов
- Отображение мастера вместо менеджера в таблице заявок
- **Отображение всех заявок**, включая заявки без устройств

### Управление клиентами и устройствами
- Полнотекстовый поиск по имени, телефону, email
- **Сортировка по умолчанию** - новые клиенты отображаются сверху (по ID)
- История заявок клиента
- Управление устройствами клиентов
- Страница истории устройства `/device/<device_id>` со всеми заявками по устройству
- Ссылки на историю устройства из таблицы заявок (поля "Устройство" и "Бренд")
- **Создание клиентов** через модальное окно с автопоиском
- **Автоматическая генерация пароля портала** при создании нового клиента
- **Управление паролем портала** в интерфейсе редактирования клиента

### Управление складом
- **Управление товарами** (`/warehouse/parts`):
  - Создание, редактирование, удаление товаров (мягкое удаление)
  - Полнотекстовый поиск по названию, артикулу, категории (регистронезависимый, по всем словам)
  - Автопоиск при вводе с задержкой 1 секунда
  - Сортировка по различным полям
  - Фильтрация по категориям (кнопки-пилюли сверху)
  - Отображение остатков, цен, маржи
  - Новый дизайн таблицы: светлая и тёмная темы, без зебры, единый стиль
- **Иерархия категорий товаров:**
  - Создание категорий и подкатегорий
  - Редактирование и удаление категорий
  - Боковое меню с отображением иерархии
  - Быстрое добавление подкатегорий
- **Поставщики:**
  - Создание, редактирование, удаление поставщиков
  - Хранение контактной информации (имя, телефон, email, адрес)
  - Выбор поставщика при создании закупок
  - История закупок по поставщику
- **Инвентаризация:**
  - Создание инвентаризационных ведомостей
  - Выбор товаров для инвентаризации
  - Сравнение ожидаемого и фактического количества
  - Автоматическая корректировка остатков (+ или -)
  - Логирование операций в движении товаров и истории склада
- **Движения товаров:**
  - Приход товара на склад
  - Списание товара со склада
  - История всех движений с разделением на ручные и автоматические операции
  - Фильтрация по типу операции (приход, расход, продажа, возврат, корректировка)
  - Автоматическое создание движения при создании товара с начальным остатком
- **История операций со складом:**
  - Логирование всех операций (создание, удаление, оприходование, списание)
  - Фильтрация по типу операции, товару, дате
  - Отображение пользователя, IP-адреса, изменений
  - Страница `/warehouse/logs` для просмотра истории

### Отчеты
- **Главный дашборд владельца** (`/`) - расширенная сводка по компании
  - Финансы: поступления, расходы, дебиторка
  - CRM: новые/активные/возвращающиеся клиенты
  - Склад: оценка склада, low-stock, закупки за период
- **Отчет по продажам** (`/reports/sales`) - объединенные продажи из заявок и магазина
  - Фильтрация по датам и клиентам
  - Отображение услуг, запчастей, общей выручки
  - Расчет оплаты и задолженности
  - Ссылки на заявки и чеки магазина
- **Отчет по закупкам** (`/reports/purchases`) - история закупок товаров
  - Фильтрация по датам и поставщикам
  - Суммы закупок и количество товаров
- **Отчет по маржинальности** (`/reports/profitability`) - анализ рентабельности
  - Включает продажи из заявок и магазина
  - Расчет прибыли по товарам и услугам
- **Отчет по остаткам** (`/reports/stock`) - текущие остатки товаров
  - Фильтрация по категориям
  - Отображение низких остатков
- **Отчет по клиентам** (`/reports/customers`) - статистика по клиентам
  - Количество заявок и продаж
  - Общая сумма продаж
- **Отчет по статьям** (`/reports/categories`) - доходы и расходы по категориям
  - Фильтрация по типам (доход/расход) и периодам
  - Группировка по категориям
- **Сводный отчёт** (`/reports/dashboard`) - расширенная сводка по компании
  - Заявки по статусам
  - Приход денег (из заявок и магазина)
  - Складские операции
  - Последние заявки и платежи
  - `/reports/summary` перенаправляет на `/reports/dashboard`
  - Период по умолчанию: последние 7 дней
- **Отчет по кассе** (`/reports/cash`) - все кассовые операции
  - Приход и расход денежных средств
  - Ссылки на источники (продажи, заявки)
  - Баланс и обороты
- **Логи действий** (`/reports/action-logs`) - история всех действий пользователей
  - Расширенная фильтрация: тип действия, объект, даты, пользователь, ID объекта, поиск по тексту
  - Чекбокс "Системные операции" для показа/скрытия системных действий
  - 25+ типов действий и 25+ типов сущностей
  - Автоматическая генерация человекочитаемых описаний
  - Ссылки на связанные объекты (заявки, клиенты, устройства)
- **Отчет по долгам сотрудников** (`/reports/salary-debts`) - задолженности персонала
  - Фильтрация по роли и статусу сотрудников
  - Детализация по каждому сотруднику
- **Отчет по зарплате** (`/reports/salary`) — карточки «Итоги» (Выручка, Итого руководителю и др.) с пояснениями формул, таблица начислений с выручкой и прибылью на уровне заявки; зарплата по заявке начисляется один раз при первом переходе в статус «начисляет зарплату» (повторное закрытие не дублирует начисления). Фиксированные правила (`fixed`) для услуг и запчастей учитывают **количество в позиции** и в заявках, и в магазине.

### Финансовый модуль
- **Касса** (`/finance/cash`) - учёт денежных операций
  - Приход и расход денежных средств, фильтрация по периодам
  - **Автоматическая синхронизация с оплатами заявок** — все оплаты автоматически создают кассовые операции (с привязкой к способу оплаты: Наличные / Перевод и др.)
  - **Автоматические записи предоплат** — предоплаты при создании заявки автоматически записываются в кассу
  - Автоматические записи при продажах через магазин
  - **Встроенная дисциплина по способам оплаты:** ручные расходы по Наличным/Переводам не позволяют уйти «в минус» по соответствующему способу оплаты (проверка остатка при создании операции)
  - **Перевод между кассами** — отдельная операция для логического перевода денег между способами оплаты (например, Перевод → Наличные); такие движения не попадают в «Приход за период»/«Расход за период», но корректно меняют остатки по Наличным и Переводам
  - Подсказка «Доложить в наличку» в карточке Наличными подсказывает, сколько нужно внести, чтобы покрыть отрицательный остаток по наличным (учитывает только реальные операции, без внутренних переводов)
- **Статьи** (`/finance/categories`) - категории доходов и расходов
  - Системные категории (продажа товаров, продажа услуг)
  - Пользовательские категории
- **Прибыль** (`/finance/profit`) - отчёт о прибыли
  - Выручка, себестоимость, расходы
  - Валовая и чистая прибыль
- **Аналитика** (`/finance/analytics`) - финансовая аналитика
  - Рентабельность
  - Оборачиваемость склада
  - Топ продаж

### Система оплат и кошелька клиента
- **Стандартизированная система оплат:**
  - **Типы платежей (kind):** `payment` (обычная оплата), `deposit` (предоплата), `refund` (возврат), `adjustment` (корректировка)
  - **Статусы платежей:** `pending` (ожидает), `captured` (подтверждён), `cancelled` (отменён), `refunded` (возвращён)
  - **Идемпотентность:** защита от дублирования платежей через `idempotency_key`
  - **Мягкая отмена:** отмена платежей с указанием причины (без физического удаления)
  - **Чеки:** система фискальных чеков (`payment_receipts`) для продаж и возвратов
- **Кошелёк клиента (депозит):**
  - Баланс клиента хранится в `customers.wallet_cents` (в копейках)
  - Полная история операций в `customer_wallet_transactions`
  - Операции: `credit` (пополнение) и `debit` (списание)
  - Автоматическая проверка баланса при списании
- **Заявки:**
  - В заявках доступна обычная оплата (наличные, карта, перевод) и возврат оплаты
  - Депозитные операции в заявках отключены (оплата с депозита, возврат в депозит, перевод переплаты в депозит)
  - Прогресс оплаты ограничен 100% (переплата не учитывается в прогрессе)

### Магазин (Быстрые продажи)
- **Быстрые продажи** (`/shop`) - продажа без создания заявки
  - Поиск по товарам и услугам
  - Корзина с расчётом суммы
  - Автоматическое списание со склада
  - Автоматическая запись в кассу
- **История продаж** - список всех продаж через магазин
- **Детали продажи** (`/shop/sale/<id>`) - информация о продаже
  - Товары и услуги
  - Себестоимость и прибыль

### Система справочников
- **Типы устройств** (`device_types`) - справочник с автопоиском
- **Бренды устройств** (`device_brands`) - справочник с автопоиском
- **Модели устройств** (`order_models`) - справочник с автопоиском
- **Симптомы** (`symptoms`) - справочник неисправностей
- **Теги внешнего вида** (`appearance_tags`) - справочник внешнего вида и комплектации
- **Менеджеры, мастера** - справочники сотрудников
- **Услуги** - справочник услуг
- **Статусы заявок** - справочник статусов

### Настройки
- **Управление пользователями и сотрудниками** (`/settings` - раздел "Пользователи и сотрудники"):
  - **Администраторы** - управление администраторами системы
    - Первый администратор защищен от удаления
  - **Мастера** - управление мастерами с индивидуальными правами доступа
    - Автоматическое создание пользователя при создании мастера
    - Настройка индивидуальных прав доступа для каждого мастера
    - Кастомные роли вида `master_{id}` с выбранными правами
  - **Менеджеры** - управление менеджерами с индивидуальными правами доступа
    - Автоматическое создание пользователя при создании менеджера
    - Настройка индивидуальных прав доступа для каждого менеджера
    - Кастомные роли вида `manager_{id}` с выбранными правами
- **Общие настройки** - часовой пояс, шаблоны печати и другие системные настройки
- **Статусы заявок** (`/settings/statuses`) - управление статусами с флагами
- **Права доступа** - управление правами и ролями пользователей

**Нормализация данных:**
- Модели устройств хранятся в `orders.model_id` (FK к `order_models`)
- Симптомы связаны через таблицу `order_symptoms` (many-to-many)
- Теги внешнего вида связаны через таблицу `order_appearance_tags` (many-to-many)
- Это обеспечивает целостность данных, быстрый поиск и аналитику

### Интерфейс и темы
- **Тёмная тема** — переключатель в меню (☀/🌙)
  - Поддержка на страницах: заявки, детали заявки, склад товаров, отчёты
  - Светлая и тёмная версии таблицы товаров `/warehouse/parts`
- **Единый дизайн** — карточки, таблицы, модальные окна адаптированы под обе темы

### Дополнительные возможности
- **Ролевая система доступа** (viewer, master, manager, admin)
  - Стандартные роли с предустановленными правами
  - **Индивидуальные права для мастеров и менеджеров** - каждый сотрудник может иметь свой набор прав
  - Кастомные роли с индивидуальными правами для каждого мастера/менеджера
  - Проверка прав через декоратор `@permission_required('permission_name')`
- Кэширование данных
- Пагинация списков
- Поиск и фильтрация
- Логирование действий
- CSRF защита
- Rate limiting

## Технологии

- **Python 3.8+**
- **Flask** - веб-фреймворк
- **Flask-Login** - аутентификация
- **Flask-WTF** - CSRF защита
- **Flask-Limiter** - rate limiting
- **PostgreSQL** - основная база данных
- **Jinja2** - шаблонизатор

## Установка

### Требования

- Python 3.8 или выше
- pip
- PostgreSQL 14+ (локально или в Docker)

### Шаги установки

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd Nika-Service-CRM
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
```

3. Активируйте виртуальное окружение:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. Установите зависимости:
```bash
pip install -r requirements.txt
```

5. Создайте файл окружения `.env`:

```bash
# Linux/macOS
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

6. Откройте `.env` в редакторе и укажите параметры подключения:

```env
SECRET_KEY=change-me-to-random-long-string
DB_DRIVER=postgres
DATABASE_URL=postgresql://postgres:111111@localhost:5432/nikacrm
APP_HOST=127.0.0.1
APP_PORT=5000
FLASK_DEBUG=True
```

Где настраивать:
- Переменные задаются в файле `.env` в корне проекта (`Nika-Service-CRM/.env`).
- Не используйте `.env.example` для реального запуска — это только шаблон.
- Файл `.env` не должен попадать в git.

7. Создайте пустую PostgreSQL базу (один раз):
```bash
createdb -h localhost -p 5432 -U postgres nikacrm
```

8. Заполните базу очищенным bootstrap-дампом:
```bash
psql -h localhost -p 5432 -U postgres -d nikacrm -f database/bootstrap/nikacrm_public_sanitized.sql
```

9. Запустите приложение:
```bash
python run.py
```

Приложение будет доступно по адресу: http://127.0.0.1:5000

**База данных:** В репозитории нет готовой рабочей файловой БД (`.db`).  
Для локального старта используйте PostgreSQL и импорт `database/bootstrap/nikacrm_public_sanitized.sql`.

### Восстановление очищенной PostgreSQL базы из репозитория

В репозитории есть безопасный SQL-дамп для локального старта:

- `database/bootstrap/nikacrm_public_sanitized.sql`

Порядок восстановления:

```bash
# 1) создать пустую БД
createdb -h localhost -p 5432 -U postgres nikacrm

# 2) залить очищенный дамп
psql -h localhost -p 5432 -U postgres -d nikacrm -f database/bootstrap/nikacrm_public_sanitized.sql
```

После восстановления для демо-входа созданы пользователи:

- `admin` / `111111`
- `manager` / `111111`
- `master` / `111111`
- `viewer` / `111111`

Важно: сразу после первого запуска смените эти пароли в своей среде.

## Структура проекта

```
Nika-Service-CRM/
├── app/                      # Основное приложение
│   ├── __init__.py          # Инициализация Flask приложения
│   ├── config.py            # Конфигурация
│   ├── database/            # Работа с БД
│   │   ├── connection.py    # Подключение к БД
│   │   ├── migrations/      # Миграции БД
│   │   ├── queries/         # SQL запросы (Query классы)
│   │   └── schema.py        # Схема БД
│   ├── middleware/          # Middleware
│   ├── models/              # Модели данных
│   ├── routes/              # Blueprint'ы (маршруты)
│   ├── services/            # Сервисы (бизнес-логика)
│   └── utils/               # Утилиты
├── templates/               # HTML шаблоны
├── static/                  # Статические файлы (CSS, JS)
├── database/                # Локальные артефакты БД (файлы БД в git не хранятся)
├── docs/                    # Документация проекта
├── scripts/                 # Служебные и миграционные скрипты
├── tests/                   # Тесты
├── run.py                   # Точка входа
├── requirements.txt         # Зависимости
└── README.md               # Этот файл
```

## Архитектура

Приложение следует многослойной архитектуре:

```
┌─────────────────┐
│   Routes (HTTP) │  ← Обработка HTTP запросов
└────────┬────────┘
         │
┌────────▼────────┐
│    Services     │  ← Бизнес-логика
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────┐
│Models │ │ Queries │  ← Работа с данными
└───┬───┘ └──┬──────┘
    │        │
    └───┬────┘
        │
┌───────▼────────┐
│   Database      │  ← PostgreSQL
└────────────────┘
```

### Слои

1. **Routes (app/routes/)** - обрабатывают HTTP запросы, возвращают HTML или JSON
2. **Services (app/services/)** - содержат бизнес-логику, валидацию, кэширование
3. **Models (app/models/)** - представляют бизнес-сущности, работа с БД
4. **Queries (app/database/queries/)** - оптимизированные SQL запросы, избежание N+1 проблем
5. **Database** - PostgreSQL база данных

Подробнее об архитектуре и модулях: [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md)

## Документация

Документация находится в папке `docs/`:
- [Руководство пользователя](docs/USER_GUIDE.md) - полное руководство по использованию системы
- [API документация](docs/API.md) - описание API endpoints
- [Обзор системы](docs/SYSTEM_OVERVIEW.md) - архитектура и ключевые модули
- [Политика данных для OSS](docs/OSS_DATA_POLICY.md) - какие данные допустимы в публичном репозитории
- [Workflow OSS-релизов](docs/OSS_RELEASE_WORKFLOW.md) - процесс синхронизации публичного репозитория

### Документация модулей

- [Сервисы](app/services/README.md) - описание всех сервисов
- [Модели](app/models/README.md) - описание моделей данных
- [Query классы](app/database/queries/README.md) - описание SQL запросов
- [Маршруты](app/routes/README.md) - описание Blueprint'ов
- [Утилиты](app/utils/README.md) - описание утилит
- [Middleware](app/middleware/README.md) - описание middleware
- [Шаблоны](templates/README.md) - описание шаблонов

---

## Руководство пользователя

### Работа с заявками
- **Создание:** Заявки → Новая заявка; заполнить клиента, устройство, неисправность, менеджера
- **Представления:** Реестр (21 колонка, настройка), Канбан, Журнал
- **Действия:** услуги, запчасти, оплаты, оплата с депозита, возврат на депозит, комментарии

### Клиенты, склад, магазин, финансы
- **Клиенты:** поиск, сортировка (новые сверху), управление паролем портала, депозит
- **Склад:** товары, категории, поставщики, инвентаризация, движения
- **Магазин:** быстрые продажи, корзина, автозапись в кассу
- **Финансы:** касса, статьи, прибыль, аналитика; ссылки на заявки и чеки

### Отчёты, уведомления, портал
- **Отчёты:** Сводный, Продажи, Касса, Зарплата, Долги, Логи; пресеты периода
- **Уведомления:** In-app, Email, Push; настройки в `/settings`
- **Портал клиента:** `/portal/login` (телефон + пароль), автогенерация пароля, смена при первом входе

### Права доступа
- Права: `view_finance`, `manage_finance`, `view_shop`, `manage_shop`, `view_action_logs`, `manage_statuses`
- Кастомным ролям сотрудников запрещено: `manage_users`, `manage_settings`

---

## API документация

**Базовый URL:** `http://127.0.0.1:5000`  
**Аутентификация:** Flask-Login (сессия + cookie)

### Заявки
| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | /all_orders | Список заявок |
| GET | /api/datatables/orders | DataTables для реестра |
| GET | /order/<order_id> | Детали (UUID или id) |
| POST | /add_order | Создание |
| PUT | /api/order/<order_id>/status | Смена статуса |

### Услуги, запчасти, оплаты
| Метод | Endpoint |
|-------|----------|
| GET/POST | /api/orders/<id>/services |
| DELETE | /api/order-services/<id> |
| GET/POST | /api/orders/<id>/parts |
| DELETE | /api/order-parts/<id> |
| GET/POST | /api/orders/<id>/payments |
| DELETE | /api/payments/<id> |
| POST | /api/payments/<id>/refund |

### Клиенты, кошелёк
| Метод | Endpoint |
|-------|----------|
| GET | /api/customers/lookup?phone=... |
| POST | /api/customers |
| PUT | /api/customers/<id> |

### Зарплата
| Метод | Endpoint |
|-------|----------|
| GET | /api/salary/report |
| POST | /api/salary/recalculate/<order_id> |
| POST | /api/salary/employee/<id>/<role>/bonus, /fine, /payment, /writeoff |

### Справочники
- `/device-types`, `/device-brands`, `/managers`, `/masters`, `/symptoms`, `/appearance-tags`, `/order-models`, `/services`, `/parts`
- `GET/POST/PATCH/DELETE /api/statuses`

### Период в отчётах
- `preset`: today, yesterday, last_7_days, last_30_days, current_month, last_month, year_to_date
- `date_from`, `date_to`: YYYY-MM-DD

### Rate limiting
- `/login`: 5/мин | `/api/statuses`: 100/час | `/api/parts`: 200/час
- По умолчанию: 200/день, 1000/час

---

## План скриптов и исправлений

### Скрипты проверки
- `scripts/check_reports_and_finance.py` — касса, прибыль, dashboard, БД
- `save/scripts/check_import_result.py` — результат импорта
- `save/scripts/check_cash_balance.py` — оплаты без проводок
- `save/scripts/create_cash_transactions_for_payments.py` — создание проводок для оплат без записи (`--dry-run`)

### Импорт
- `save/scripts/import_from_old_crm.py` — импорт из старой CRM (создаёт проводки в кассе)
- `save/scripts/import_profit_orders_v2.py` — импорт заявок
- `save/scripts/fix_salary_for_imported_orders.py` — начисление зарплаты по импортированным заявкам

---

## Маршруты и сервисы

### Blueprints
- **orders:** /add_order, /all_orders, /order/<id>, /device/<id>
- **customers:** /clients, /clients/<id>
- **main:** /, /login, /logout
- **settings:** /settings, /settings/statuses
- **api:** /api/*
- **warehouse:** /warehouse/*
- **reports:** /reports/*
- **finance:** /finance/*
- **shop:** /shop
- **salary:** /salary

### Сервисы
- **OrderService:** create_order, get_orders_with_details, add_order_service, add_order_part, update_order_status, sell_items
- **CustomerService:** get_customer, create_customer, search_customers
- **DeviceService, ReferenceService, PaymentService, WarehouseService, ReportsService**

---

## Полный справочник системы (по результатам сканирования кода)

### Все маршруты (Routes) с полными URL

#### Main (`/`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | / | Главная (дашборд) |
| GET/POST | /login | Вход |
| GET | /logout | Выход |
| GET | /notifications | Уведомления |
| GET/POST | /settings | Настройки |
| GET | /settings/employees | Пользователи и сотрудники |
| GET | /settings/user-permissions | Права пользователей |

#### Orders (без префикса)
| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | /add_order | Создание заявки |
| GET | /all_orders | Список заявок |
| GET | /order/<order_id> | Детали заявки |
| POST | /order/<order_id> | Редактирование заявки |
| GET | /device/<device_id> | История устройства |
| GET | /api/datatables/orders | DataTables реестра |
| PUT | /api/order/<order_id>/status | Смена статуса |
| POST | /api/order/<order_id>/comment | Добавить комментарий |
| DELETE | /api/order/comment/<id> | Удалить комментарий |
| POST | /api/order/<order_id>/toggle-visibility | Скрыть/показать заявку |
| POST | /api/orders/check_duplicate | Проверка дубликатов |
| GET/POST | /api/orders/<id>/services | Услуги заявки |
| DELETE | /api/order-services/<id> | Удалить услугу |
| PATCH | /api/order-services/<id> | Редактировать услугу |
| GET/POST | /api/orders/<id>/payments | Оплаты |
| DELETE | /api/payments/<id> | Отменить оплату |
| POST | /api/payments/<id>/refund | Возврат |
| GET/POST | /api/payments/<id>/receipts | Чеки |
| GET/POST | /api/orders/<id>/parts | Запчасти |
| DELETE | /api/order-parts/<id> | Удалить запчасть |
| PATCH | /api/order-parts/<id> | Редактировать запчасть |
| GET | /api/orders/items/price-history | История цен |
| POST | /api/orders/<id>/sell | Объединённая продажа |
| GET | /api/search/items | Поиск товаров/услуг |
| GET | /receipts/<id>/print | Печать чека |

#### Customers (`/clients`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /clients | Список клиентов |
| GET | /clients/<id> | Карточка клиента |
| GET | /clients/<id>/create_order | Создать заявку для клиента |
| GET | /api/datatables/clients | DataTables клиентов |
| GET | /api/customers/lookup?phone=... | Поиск по телефону |
| POST | /api/customers | Создать клиента |
| GET/PUT/DELETE | /api/customers/<id> | Клиент CRUD |
| POST/DELETE | /api/customers/<id>/portal-password | Пароль портала |
| GET | /api/customers/<id>/portal-password/show | Показать пароль |
| POST | /api/clients/<id>/devices | Добавить устройство |
| PUT/DELETE | /api/clients/<id>/devices/<device_id> | Устройство CRUD |

#### API Settings (`/api`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | /api/settings/users | Пользователи |
| GET/PATCH/DELETE | /api/settings/users/<id> | Пользователь |
| POST | /api/settings/users/<id>/change-password | Смена пароля |
| GET | /api/settings/permissions | Права |
| PATCH | /api/settings/permissions/<id> | Право |
| GET/POST | /api/settings/roles | Роли |
| GET/PATCH/DELETE | /api/settings/roles/<role> | Роль |

#### Warehouse (`/warehouse`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /warehouse, /warehouse/parts | Товары |
| GET/POST | /warehouse/parts/new | Новый товар |
| GET | /warehouse/parts/<id> | Карточка товара |
| GET/POST | /warehouse/parts/<id>/edit | Редактировать |
| POST | /warehouse/parts/<id>/delete, /restore | Удалить/восстановить |
| POST | /warehouse/parts/<id>/income | Оприходование |
| POST | /warehouse/parts/<id>/expense | Списание |
| GET/POST | /warehouse/categories | Категории |
| PUT/DELETE | /warehouse/categories/<id> | Категория |
| GET | /warehouse/api/parts | API товаров |
| GET | /warehouse/logs | История операций |
| GET | /warehouse/purchases | Закупки |
| GET/POST | /warehouse/purchases/new | Новая закупка |
| GET | /warehouse/purchases/<id> | Детали закупки |
| GET/POST | /warehouse/purchases/<id>/edit | Редактировать |
| POST | /warehouse/purchases/<id>/delete, /complete | Удалить/завершить |
| GET | /warehouse/movements | Движения товаров |
| POST | /api/warehouse/adjust-stock | Корректировка остатка |
| GET | /warehouse/suppliers | Поставщики |
| GET/POST | /warehouse/suppliers/new | Новый поставщик |
| GET | /warehouse/suppliers/<id> | Карточка поставщика |
| GET/POST | /warehouse/suppliers/<id>/edit | Редактировать |
| POST | /warehouse/suppliers/<id>/delete | Удалить |
| GET | /warehouse/inventory | Инвентаризация |
| GET/POST | /warehouse/inventory/new | Новая инвентаризация |
| GET | /warehouse/inventory/<id> | Детали |
| POST | /warehouse/inventory/<id>/complete | Завершить |

#### Finance (`/finance`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /finance/categories | Статьи |
| GET/POST | /finance/api/categories | API статей |
| PUT/DELETE | /finance/api/categories/<id> | Статья |
| GET | /finance/cash | Касса |
| POST | /finance/api/transactions | Создать операцию |
| DELETE | /finance/api/transactions/<id> | Удалить операцию |
| GET | /finance/profit | Прибыль |
| GET | /finance/analytics | Аналитика |
| GET | /finance/payment/<id> | Детали оплаты/чека |

#### Shop (`/shop`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /shop/ | Магазин (быстрые продажи) |
| GET | /shop/sale/<id> | Детали продажи |
| POST | /shop/api/sales | Создать продажу |
| POST | /shop/api/sales/<id>/refund | Возврат |
| DELETE | /shop/api/sales/<id> | Удалить продажу |
| GET | /shop/api/search | Поиск товаров/услуг |
| GET | /shop/api/customers/search | Поиск клиентов |

#### Reports (`/reports`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /reports/stock | Остатки |
| GET | /reports/purchases | Закупки |
| GET | /reports/sales | Продажи |
| GET | /reports/profitability | Маржинальность |
| GET | /reports/categories | Статьи |
| GET | /reports/customers | Клиенты |
| GET | /reports/cash | Касса |
| GET | /reports/orders-log | Журнал заявок |
| GET | /reports/summary | Сводный (→ dashboard) |
| GET | /reports/action-logs | Логи действий |
| GET | /reports/dashboard | Дашборд отчётов |
| GET | /reports/api/dashboard | API дашборда |
| GET | /reports/salary | Зарплата |
| GET | /reports/salary-debts | Долги сотрудников |

#### Salary (`/salary`, `/api/salary`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /salary | Модуль зарплаты |
| GET | /salary/employee/<id>/<role> | Кабинет сотрудника |
| GET | /api/salary/employees | Список сотрудников |
| GET | /api/salary/employee/<id>/<role> | Данные сотрудника |
| POST | /api/salary/employee/<id>/<role>/bonus | Премия |
| POST | /api/salary/employee/<id>/<role>/fine | Штраф |
| POST | /api/salary/employee/<id>/<role>/payment | Выплата |
| POST | /api/salary/employee/<id>/<role>/writeoff | Списание долга |
| GET | /api/salary/debts | Долги |
| GET | /api/salary/report | Отчёт |
| POST | /api/salary/recalculate/<order_id> | Пересчёт |
| GET | /api/salary/order/<order_id> | Начисления по заявке |

#### Statuses (`/api/statuses`), Settings page (`/settings/statuses`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /settings/statuses | Страница статусов |
| GET | /api/statuses | Список статусов |
| GET | /api/statuses/<id> | Статус |
| POST | /api/statuses | Создать |
| PATCH | /api/statuses/<id> | Обновить |
| POST | /api/statuses/<id>/archive | В архив |
| POST | /api/statuses/<id>/unarchive | Из архива |
| DELETE | /api/statuses/<id> | Удалить |
| POST | /api/statuses/reorder | Изменить порядок |

#### Settings — справочники (`/api`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | /api/device-types | Типы устройств |
| PUT/DELETE | /api/device-types/<id> | Тип |
| POST | /api/device-types/update-sort-order | Сортировка |
| GET | /api/device-types/<id>/usage | Использование |
| GET/POST | /api/device-brands | Бренды |
| PUT/DELETE | /api/device-brands/<id> | Бренд |
| POST | /api/device-brands/update-sort-order | Сортировка |
| GET | /api/device-brands/<id>/usage | Использование |
| GET | /api/order-tags | Теги заявок |
| GET/POST | /api/order-models | Модели |
| PUT/DELETE | /api/order-models/<id> | Модель |
| GET | /api/order-models/<id>/usage | Использование |
| GET/POST | /api/symptoms | Симптомы |
| PUT/DELETE | /api/symptoms/<id> | Симптом |
| POST | /api/symptoms/update-sort-order | Сортировка |
| GET | /api/symptoms/<id>/usage | Использование |
| GET/POST | /api/appearance-tags | Теги внешнего вида |
| PUT/DELETE | /api/appearance-tags/<id> | Тег |
| POST | /api/appearance-tags/update-sort-order | Сортировка |
| GET | /api/appearance-tags/<id>/usage | Использование |
| GET/POST | /api/services | Услуги |
| PUT/DELETE | /api/services/<id> | Услуга |
| POST | /api/services/update-sort-order | Сортировка |
| GET | /api/services/<id>/usage | Использование |

#### Masters (`/api/masters`), Managers (`/api/managers`), Employees (`/api/employees`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /api/masters | Мастера |
| GET/POST | /api/masters, /api/masters/<id> | CRUD мастера |
| PATCH/DELETE | /api/masters/<id> | Обновить/удалить |
| GET | /api/managers | Менеджеры |
| GET/POST | /api/managers, /api/managers/<id> | CRUD менеджера |
| PATCH/DELETE | /api/managers/<id> | Обновить/удалить |
| GET/POST | /api/employees | Сотрудники |
| PATCH/DELETE | /api/employees/<id> | Обновить/удалить |

#### Search (`/search`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /search | Результаты поиска |
| GET | /search/api/autocomplete | Автодополнение |
| GET | /search/api | API поиска |

#### Templates (`/api/templates`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | /api/templates | Шаблоны заявок |
| GET | /api/templates/<id> | Шаблон |
| PUT/PATCH/DELETE | /api/templates/<id> | CRUD |

#### Tasks (`/api/tasks`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | /api/tasks | Задачи |
| GET | /api/tasks/<id> | Задача |
| PUT/PATCH/DELETE | /api/tasks/<id> | CRUD |
| GET | /api/tasks/overdue | Просроченные |

#### Notifications (`/api/notifications`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /api/notifications | Уведомления |
| GET | /api/notifications/unread-count | Счётчик непрочитанных |
| POST | /api/notifications/<id>/read | Отметить прочитанным |
| POST | /api/notifications/read-all | Все прочитаны |
| GET/POST | /api/notifications/preferences | Настройки |

#### Comments (`/api/comments`)
| Метод | URL | Описание |
|-------|-----|----------|
| POST | /api/comments/upload | Загрузка вложения |
| GET | /api/comments/attachment/<id> | Получить вложение |

#### Action logs
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /action-logs | Логи действий |
| GET | /action-logs/<entity_type>/<id> | Логи по объекту |

#### Customer Portal (`/portal`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET/POST | /portal/login | Вход в портал |
| POST | /portal/logout | Выход |
| GET | /portal, /portal/dashboard | Дашборд клиента |
| GET | /portal/orders | Мои заявки |
| GET | /portal/payments | Мои платежи |
| GET | /portal/wallet | Кошелёк |

#### API Parts (`/api/parts`)
| Метод | URL | Описание |
|-------|-----|----------|
| GET | /api/parts | Список товаров |

---

### Все шаблоны (Templates)

| Шаблон | URL/назначение |
|--------|----------------|
| base.html | Базовый layout |
| auth/login.html | Вход |
| dashboard.html | Дашборд |
| add_order.html | Форма создания заявки |
| all_orders.html | Список заявок |
| order_detail.html | Детали заявки |
| client_detail.html | Карточка клиента |
| clients.html | Список клиентов |
| device_history.html | История устройства |
| error.html, errors/404.html, errors/500.html | Ошибки |
| notifications.html | Уведомления |
| **finance/** | |
| finance/cash.html | Касса |
| finance/categories.html | Статьи |
| finance/analytics.html | Аналитика |
| finance/profit.html | Прибыль |
| finance/payment_detail.html | Детали оплаты |
| finance/payment_receipt_print.html | Печать чека |
| **portal/** | |
| portal/base.html, login.html | Портала клиента |
| portal/dashboard.html | Дашборд клиента |
| portal/orders.html | Заявки клиента |
| portal/payments.html | Платежи |
| portal/wallet.html | Кошелёк |
| **reports/** | |
| reports/dashboard.html, summary.html | Сводный |
| reports/sales.html | Продажи |
| reports/cash.html | Касса |
| reports/salary_debts.html | Долги |
| reports/action_logs.html | Логи |
| reports/customers.html, stock.html | Клиенты, остатки |
| reports/profitability.html, purchases.html | Маржинальность, закупки |
| reports/categories.html, orders_log.html | Статьи, журнал |
| **salary/** | |
| salary/index.html | Модуль зарплаты |
| salary/employee_detail.html | Кабинет сотрудника |
| salary/report.html | Отчёт |
| **search/** | |
| search/results.html | Результаты поиска |
| **settings/** | |
| settings.html | Общие настройки |
| settings/employees.html | Сотрудники |
| settings/statuses.html | Статусы |
| settings/user_permissions.html | Права |
| **shop/** | |
| shop/index.html | Магазин |
| shop/sale_detail.html | Детали продажи |
| **warehouse/** | |
| warehouse/parts_list.html | Товары |
| warehouse/part_detail.html, part_form.html | Товар |
| warehouse/logs.html | История |
| warehouse/movements.html | Движения |
| warehouse/suppliers_list.html | Поставщики |
| warehouse/purchases.html | Закупки |
| warehouse/inventory_*.html | Инвентаризация |
| **partials/** | |
| partials/sidebar.html | Боковое меню |
| partials/navbar.html | Навбар |
| partials/period_filter.html | Фильтр периода |
| partials/reports_menu.html, settings_sidebar.html | Меню |

---

### Все сервисы (Services)

| Сервис | Назначение |
|--------|------------|
| OrderService | Заявки: create, update, status, services, parts, payments, sell |
| CustomerService | Клиенты: CRUD, поиск, статистика |
| DeviceService | Устройства: CRUD, история |
| ReferenceService | Справочники: типы, бренды, модели, симптомы, теги, услуги |
| PaymentService | Оплаты: добавление, возврат, отмена |
| CommentService | Комментарии: CRUD, вложения |
| UserService | Пользователи: аутентификация, права |
| SettingsService | Настройки: общие, шаблоны печати |
| WarehouseService | Склад: товары, категории, движения, закупки, инвентаризация |
| ReportsService | Отчёты: продажи, касса, прибыль и др. |
| ActionLogService | Логи действий |
| BackupService | Резервное копирование |
| CustomerPortalService | Портала клиента |
| DashboardService | Дашборд владельца |
| FinanceService | Финансы: касса, операции |
| ManagerService, MasterService | Менеджеры, мастера |
| NotificationService | Уведомления |
| ReceiptService | Чеки |
| SalaryService | Зарплата |
| SalaryDashboardService | Дашборд зарплаты |
| SearchService | Полнотекстовый поиск (FTS5) |
| StatusService | Статусы заявок |
| TaskService | Задачи |
| TemplateService | Шаблоны заявок |
| WalletService | Кошелёк клиента |

---

### Модели данных (Models)

| Модель | Таблица | Назначение |
|--------|---------|------------|
| Customer | customers | Клиенты |
| Device | devices | Устройства |
| Order | orders | Заявки |
| Service | services | Услуги (справочник) |
| Part | parts | Товары |
| Payment | payments | Оплаты |
| User | users | Пользователи |
| Purchase | purchases | Закупки |
| StockMovement | stock_movements | Движения товаров |

---

### Query классы (database/queries)

| Класс | Назначение |
|-------|------------|
| OrderQueries | Заявки, JOIN, фильтры |
| CustomerQueries | Клиенты |
| DeviceQueries | Устройства |
| ReferenceQueries | Справочники |
| PaymentQueries | Оплаты |
| CommentQueries | Комментарии |
| ReceiptQueries | Чеки |
| SalaryQueries | Зарплата |
| StatusQueries | Статусы |
| WalletQueries | Кошелёк |
| WarehouseQueries | Склад |

---

### Утилиты (utils)

| Утилита | Назначение |
|---------|------------|
| action_logger | Логирование действий |
| api_validators | Валидация API |
| cache, cache_helpers | Кэширование |
| datetime_utils | Работа с датами |
| db_error_translator | Перевод ошибок БД |
| error_handlers | Обработка ошибок |
| exceptions | Исключения |
| pagination | Пагинация |
| performance_monitor | Мониторинг |
| report_period | Период отчётов |
| validators | Валидаторы |

---

### Context processors (глобальные в шаблонах)

- `has_permission(name)` — проверка права
- `has_any_permission(*names)` — любое из прав
- `get_user_display_name(user_id, username)` — отображаемое имя
- `csrf_token()` — CSRF токен
- `format_date` — фильтр даты (ДД.ММ.ГГГГ)

---

### Расширения Flask

- Flask-Login, Flask-WTF, Flask-Limiter, CSRFProtect
- Flask-Mail (опционально)
- Flask-SocketIO (опционально, push-уведомления)

---

### Основные скрипты (scripts/)

| Скрипт | Назначение |
|--------|------------|
| migrate.py | Миграции БД |
| create_cash_transactions_for_payments.py | Проводки для оплат без записи |
| import_from_old_crm.py | Импорт из старой CRM |
| import_profit_orders_v2.py | Импорт заявок |
| fix_salary_for_imported_orders.py | Зарплата по импорту |
| accrue_salary_for_order.py | Начисление зарплаты |
| check_reports_and_finance.py | Проверка отчётов и кассы |
| check_import_result.py | Результат импорта |
| check_cash_balance.py | Баланс кассы |
| audit_permissions.py | Аудит прав |
| check_user_permissions.py | Права пользователя |
| create_backup.py | Резервная копия |
| add_recommended_indexes.py | Индексы БД |
| backfill_initial_stock_movements.py | Заполнение движений |
| import_clients_xlsx.py | Импорт клиентов |
| import_services_parts.py | Импорт услуг/товаров |

---

## Использование

### Создание заявки

```python
from app.services import OrderService

order_data = {
    'customer_name': 'Иван Иванов',
    'phone': '+79991234567',
    'device_type_id': 1,
    'device_brand_id': 1,
    'manager_id': 1,
    'prepayment': 1000.00
}

order = OrderService.create_order(**order_data)
```

### Получение списка заявок

```python
from app.services import OrderService

filters = {'status': 'new', 'customer_id': 1}
paginator = OrderService.get_orders_with_details(filters, page=1, per_page=50)

for order in paginator.items:
    print(order.id, order.client_name)
```

### Работа с клиентами

```python
from app.services import CustomerService

# Поиск клиента
customer = CustomerService.get_customer_by_phone('+79991234567')

# Создание клиента
customer = CustomerService.create_customer({
    'name': 'Иван Иванов',
    'phone': '+79991234567',
    'email': 'ivan@example.com'
})
```

Больше примеров: [app/services/README.md](app/services/README.md)

## Конфигурация

Настройки приложения находятся в `app/config.py`:

- `SECRET_KEY` - секретный ключ для сессий (обязательно в продакшене!)
- `DB_DRIVER` - драйвер БД (`postgres` по умолчанию)
- `DATABASE_URL` - строка подключения PostgreSQL
- `APP_PORT` - порт локального запуска (`5000` по умолчанию)
- `DEBUG` - режим отладки
- `LOG_LEVEL` - уровень логирования

Для продакшена установите переменные окружения:

```bash
export SECRET_KEY=your-secret-key-here
export FLASK_DEBUG=False
```

## Миграции базы данных

Система использует миграции для управления схемой БД:

```bash
# Применить все непримененные миграции
python scripts/run_migrations.py
```

## Тестирование

Запуск тестов:

```bash
pytest
```

Запуск с покрытием:

```bash
pytest --cov=app
```

## Разработка

### Добавление нового сервиса

1. Создайте файл `app/services/your_service.py`
2. Реализуйте класс с статическими методами
3. Используйте валидацию и обработку ошибок
4. Экспортируйте в `app/services/__init__.py`

Подробнее: [app/services/README.md](app/services/README.md)

### Добавление нового маршрута

1. Создайте файл `app/routes/your_blueprint.py`
2. Создайте Blueprint
3. Определите маршруты с декораторами
4. Зарегистрируйте в `app/__init__.py`

Подробнее: [app/routes/README.md](app/routes/README.md)

## Безопасность

### Реализованные меры безопасности

#### Хеширование паролей
- **Использование werkzeug.security** (pbkdf2:sha256, scrypt, argon2) вместо SHA-256
- **Автоматическая миграция** старых SHA-256 хешей при входе пользователя
- **Поддержка всех форматов werkzeug** (pbkdf2, scrypt, argon2) для обратной совместимости
- **Безопасное хеширование** с солью для защиты от rainbow tables

#### Защита от атак

- **Параметризованные SQL запросы** - защита от SQL injection
- **CSRF защита** - все формы защищены через Flask-WTF
- **Rate limiting** - защита от brute-force и злоупотреблений:
  - `/login`: 5 попыток в минуту
  - `/api/statuses`: 100 запросов в час
  - `/api/parts`: 200 запросов в час
  - По умолчанию: 200 запросов в день, 1000 в час
- **Безопасное хеширование паролей** - используется `werkzeug.security` (pbkdf2:sha256) с солью
- **Автоматическая миграция паролей** - старые SHA-256 пароли автоматически перехешируются при входе
- **Ролевая система доступа:**
  - Стандартные роли: viewer, master, manager, admin
  - **Индивидуальные права для мастеров и менеджеров** - каждый сотрудник может иметь свой набор прав
  - Кастомные роли с индивидуальными правами (`master_{id}`, `manager_{id}`)
  - Проверка прав через `@permission_required('permission_name')` декоратор
- **Фильтрация чувствительных данных в логах** - пароли, токены и секреты автоматически скрываются
- **HTTPS для продакшена** - настройки безопасности cookies и принудительное использование HTTPS

### Рекомендации для продакшена

1. **Установите SECRET_KEY** через переменную окружения:
   ```bash
   export SECRET_KEY=your-very-secret-key-here
   ```

2. **Используйте HTTPS** - настройте reverse proxy (nginx, Apache) с SSL сертификатом

3. **Регулярно обновляйте зависимости** - проверяйте уязвимости через `pip list --outdated`

4. **Настройте резервное копирование БД** - регулярно создавайте бэкапы базы данных

5. **Мониторинг** - настройте логирование и мониторинг ошибок

Подробнее: [SECURITY.md](SECURITY.md)

## Производительность

- **Кэширование справочников** - TTL 1 час для часто используемых данных
- **In-memory кэш с LRU политикой** - максимальный размер 1000 записей, автоматическое вытеснение старых
- **Оптимизированные SQL запросы** - использование JOIN вместо N+1 проблем
- **Индексы базы данных** - автоматически создаются через миграции
- **Пагинация больших списков** - по умолчанию 50 элементов на странице, максимум 200
- **Ленивая загрузка данных** - данные загружаются только при необходимости

Подробнее: [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md)

## История изменений

### Последние изменения (2026-03-02)

#### Тёмная тема и интерфейс
- **Тёмная тема** — переключатель в меню (светлая/тёмная)
- Поддержка тёмной темы на страницах: заявки, детали заявки, склад товаров, отчёты
- **Таблица товаров** (`/warehouse/parts`) — новый дизайн, светлая и тёмная версии без зебры
- Период отчётов по умолчанию: последние 7 дней

#### Структура проекта
- Папка `save/` — скрипты, документация, тесты, резервные копии БД
- Вспомогательные файлы создаются в `save/` с описанием назначения

### (2026-01-31)

#### Таблица заявок и отчёт по зарплате (2026-01-29)
- **Реестр заявок (/all_orders):** Расширенная таблица (21 колонка), скрытие колонок, верхняя горизонтальная прокрутка, перетаскивание колонок
- **Отчёт по зарплате (/reports/salary):** Выручка и прибыль на уровне заявки, карточки «Итоги», учёт себестоимости товаров и услуг

#### Касса, импорт и ссылки (2026-01-28)
- **Проводки:** скрипт `create_cash_transactions_for_payments.py` для оплат без записи в кассе
- **Импорт:** автоматическое создание проводок при импорте заявок
- **Касса:** ссылки «Заявка #N» и «Чек #N» в списке операций

#### Исправления
- Зарплата начисляется один раз при первом переходе в статус «Начисляет зарплату»
- Период по умолчанию до «сегодня», пресеты «Квартал» и «Полгода»

### Последние изменения (2026-01-28)

#### Новые функции портала клиента
- Автоматическая генерация пароля при создании клиента
- Обязательная смена пароля при первом входе
- Управление паролем в интерфейсе редактирования клиента

### Последние изменения (2026-01-26)

#### Реализованы 9 крупных функций
- Система уведомлений (Email/Push), расширенная система комментариев
- Система задач и дедлайнов, шаблоны заявок
- Продвинутая аналитика, глобальный поиск (FTS5)
- Мобильная версия / PWA, личный кабинет клиента

---

### Версия 1.8 (2026-01-20)

#### Исправления ошибок и улучшения
- ✅ **Исправлена ошибка UndefinedError в dashboard** - добавлена проверка на существование `data.summary` для предотвращения падения при ошибках загрузки данных
- ✅ **Исправлено меню фильтров в action-logs** - оптимизирована структура Bootstrap grid, кнопки "Применить" и "Сбросить" теперь правильно позиционированы
- 🚀 **Расширенная система логов действий** - добавлено 25+ типов действий и 25+ типов сущностей с улучшенными фильтрами
- 📊 **Новый отчет по долгам сотрудников** (`/reports/salary-debts`) - анализ задолженностей персонала
- 🔍 **Улучшенные фильтры action-logs**: чекбокс системных операций, полнотекстовый поиск, фильтрация по ID объекта
- 🤖 **Автоматическая генерация описаний** - человекочитаемые описания вместо технических терминов
- 🔄 **Убрана бесконечная рекурсия** - просмотр action-logs больше не создает записи в самих логах

---

### Версия 1.7 (2026-01-18)

#### Система индивидуальных прав доступа для мастеров и менеджеров
- **Индивидуальные права для каждого сотрудника:**
  - При создании мастера/менеджера можно выбрать конкретные права доступа
  - Каждому мастеру/менеджеру автоматически создается кастомная роль (`master_{id}`, `manager_{id}`)
  - Права сохраняются в таблице `role_permissions` и проверяются при каждом запросе
  - Система прав работает автоматически через декоратор `@permission_required`
- **Автоматическое создание пользователей:**
  - При создании мастера/менеджера автоматически создается пользователь с логином и паролем
  - Имя мастера/менеджера используется как имя пользователя (username)
  - Связь между пользователем и мастером/менеджером поддерживается через `user_id`
- **Объединенное управление в настройках:**
  - Все управление пользователями, мастерами и менеджерами объединено в один раздел `/settings` - "Пользователи и сотрудники"
  - Удалены старые роуты `/settings/masters` и `/settings/managers`
  - Три вкладки: Администраторы, Мастера, Менеджеры

#### Исправления
- Улучшено логирование проверки прав для отладки
- Добавлена валидация `permission_ids` при создании мастеров и менеджеров

### Версия 1.8 (2026-01-20)

#### Модуль зарплаты
- Добавлены карточки сотрудников в табах "Мастера/Менеджеры" на `/salary`
- Добавлен таб "Долги" на `/salary` и отчет `/reports/salary-debts`
- В личном кабинете сотрудника: отображение отрицательного долга и кнопка "Списать долг"
- "К выплате" теперь учитывает премии и штрафы (может быть отрицательным)
- Выручка/прибыль/заявки в `/salary` считаются по начислениям за период
- Выплаты в кассе фиксируются как расход с указанием сотрудника

#### Доводка RBAC (2026-01-20)
- **Новые права модулей:**
  - `view_finance`, `manage_finance` (финансы)
  - `view_shop`, `manage_shop` (магазин)
  - `view_action_logs` (логи действий)
  - `manage_statuses` (управление статусами)
- **Применено на маршрутах (серверная защита):**
  - Склад: `view_warehouse` / `manage_warehouse`
  - Финансы: `view_finance` / `manage_finance`
  - Магазин: `view_shop` / `manage_shop`
  - Логи: `view_action_logs`
  - Статусы: чтение статусов = `view_orders`, изменения = `manage_statuses`
- **UX:** пункты меню/сайдбар скрываются по правам (через `has_permission()` в шаблонах).
- **Ограничение безопасности:** кастомным ролям сотрудников (например, `master_33`, `manager_12`) **запрещено** выдавать права `manage_users` и `manage_settings`.

#### Как проверить права
- **Список прав/назначений ролям:**
  - `python scripts/audit_permissions.py`
- **Проверка конкретного пользователя:**
  - `python scripts/check_user_permissions.py <username>`

### Версия 1.6 (2026-01-18)

#### Исправления
- ✅ Исправлена ошибка `UnboundLocalError` при добавлении платежей для закрытых заявок
- ✅ Убраны все повторные импорты `OrderService`, вызывающие ошибки
- ✅ Разрешено добавление платежей для закрытых заявок (при закрытии заявки)
- ✅ Улучшена обработка ошибок валидации при добавлении запчастей
- ✅ Добавлено логирование просмотра заявок
- ✅ Исправлена обработка дублирования истории статусов

#### Тестирование
- ✅ Созданы тесты безопасности API (65 тестов)
- ✅ Созданы тесты валидации данных (17 тестов)
- ✅ Созданы тесты складских операций (9 тестов)
- ✅ Все 62 теста проходят успешно
- ✅ Проверена безопасность всех 61 API endpoint

#### Документация
- ✅ Созданы README для всех модулей (services, routes, models, queries)
- ✅ Обновлена API документация
- ✅ Обновлено руководство пользователя
- ✅ Добавлена документация по безопасности API

### Версия 1.5 (2026-01-16)

- Отчет по зарплате перенесен в `/reports/salary` и добавлен в меню отчетов
- Управление статусами вынесено в отдельную страницу `/settings/statuses`
- Добавлены флаги статусов (оплата, зарплата, финальный, блокировка, гарантия, комментарий, архив)
- Для отчета продаж включен безопасный дефолтный период (текущий месяц)

### Версия 1.4 (2026-01-05)

#### Стандартизация системы оплат
- **Типы и статусы платежей:**
  - Типы платежей: `payment`, `deposit`, `refund`, `adjustment`
  - Статусы: `pending`, `captured`, `cancelled`, `refunded`
  - Идемпотентность через `idempotency_key` для защиты от дублирования
- **Мягкая отмена платежей:**
  - Отмена платежей с указанием причины (роль `manager` и выше)
  - Создание сторно-операций в кассе для отменённых платежей
  - Сохранение истории платежей без физического удаления
- **Система чеков:**
  - Таблица `payment_receipts` для фискальных чеков
  - Поддержка чеков продажи и возврата
  - Ручное создание чеков через API

#### Кошелёк клиента (депозит)
- **Баланс и операции:**
  - Поле `customers.wallet_cents` для хранения баланса в копейках
  - Таблица `customer_wallet_transactions` для полной истории операций
  - Операции `credit` (пополнение) и `debit` (списание) с проверкой баланса
- **Важно:**
  - Депозитные операции в интерфейсе заявки отключены
  - Кошелек клиента не используется напрямую в оплатах заявки

### Версия 1.3 (2025-12-22)

#### Синхронизация оплат и кассы
- **Автоматическая синхронизация оплат с кассой:**
  - При добавлении оплаты к заявке автоматически создается кассовая операция
  - При удалении оплаты автоматически удаляется соответствующая кассовая операция
  - Все оплаты отображаются в финансовых отчетах и модуле кассы
- **Предоплата в кассе:**
  - При создании заявки с предоплатой автоматически создается кассовая операция
  - Предоплата учитывается в финансовых отчетах
  - Созданы кассовые операции для всех существующих заявок с предоплатой
- **Улучшенные описания в логах:**
  - Оплаты в action_logs отображаются с человекочитаемыми описаниями
  - Типы оплаты переведены на русский язык (наличные, карта, перевод)

#### Исправления отчетов
- **Отчет по продажам (/reports/sales):**
  - Исправлена фильтрация: учитываются заявки с оплатами в указанном периоде
  - Заявки отображаются даже если созданы раньше, но оплата была в периоде
- **Отчет по кассе (/reports/cash):**
  - Устранено дублирование операций (показываются только из cash_transactions)
  - Оплаты из payments автоматически включены через синхронизацию
- **Аналитика (/finance/analytics):**
  - Добавлены продажи товаров из заявок (order_parts) в дополнение к магазинным продажам
  - Полная картина продаж по всем каналам

#### Исправления базы данных
- Исправлена ошибка с колонкой `op.created_at` в аналитике
- Исправлена ошибка с `p.payment_date` в отчете продаж

### Версия 1.2 (2025-12-21)

#### Исправления отчетов
- Исправлена ошибка с параметрами SQL в сводном отчете
- Добавлены платежи из магазина в раздел "Последние платежи"
- Улучшен расчет прихода денег (объединение оплат из заявок и магазина)
- Исправлено отображение ID заявки в отчете продаж (порядковый номер вместо UUID)
- Добавлены ссылки на клиентов в отчете продаж
- Добавлена колонка "Задолженность" в отчете продаж
- Включены продажи из магазина в отчет по прибыльности

#### Улучшения меню
- Добавлен пункт "Статьи" в боковое меню всех отчетов
- Актуализированы все ссылки в верхнем и боковом меню

#### Интеграция магазинных продаж
- Унифицировано отображение продаж из заявок и магазина во всех отчетах
- Улучшена связность данных: клиенты, заявки, магазинные продажи

### Версия 1.1 (2025-12-20)

#### Финансовый модуль
- Модуль "Касса" для учёта денежных операций
- Категории (статьи) доходов и расходов
- Отчёт о прибыли (выручка, себестоимость, расходы)
- Финансовая аналитика (рентабельность, оборачиваемость, топ продаж)
- Поддержка отрицательного баланса с визуальным предупреждением

#### Модуль "Магазин"
- Быстрые продажи без создания заявки
- Автоматическое списание со склада
- Автоматическая запись в кассу
- История продаж с детализацией

#### Улучшения отчётов
- Фильтр периода во всех отчётах (сегодня, вчера, неделя, месяц и т.д.)
- Сводный отчёт с общей статистикой
- Интеграция логов действий в раздел отчётов

### Версия 1.0 (2025-01-XX)

#### Новые функции
- Поле "Модель" устройства с автопоиском (при создании и редактировании заявки)
- Ссылки на историю устройства из таблицы заявок (поля "Устройство" и "Бренд")
- Улучшенное отображение неисправностей и внешнего вида в виде тегов
- Отображение мастера вместо менеджера в таблице заявок
- Динамическая смена статуса с цветными уведомлениями (в списке заявок и на странице заявки)
- Отображение всех заявок, включая заявки без устройств
- Сортировка клиентов по умолчанию (новые клиенты сверху)
- Удаление дубля поиска в списке клиентов
- Исправление формы редактирования заявки (device_types, device_brands, модель)
- Система уведомлений о смене статуса с цветовой индикацией

#### Улучшения безопасности
- Замена SHA-256 на werkzeug.security (pbkdf2:sha256, scrypt, argon2) для хеширования паролей
- Автоматическая миграция старых SHA-256 паролей при входе пользователя
- Поддержка всех форматов werkzeug для обратной совместимости
- Rate limiting на критичные endpoints (login, API endpoints)
- Фильтрация чувствительных данных в логах
- Настройки HTTPS для продакшена (secure cookies, forced HTTPS)
- Исправление CSRF защиты для создания клиентов

#### Улучшения производительности
- LRU политика для in-memory кэша
- Ограничение размера кэша (1000 записей)
- Оптимизация SQL запросов
- Исправление LEFT JOIN для отображения всех заявок (включая без устройств)

#### Улучшения интерфейса
- Валидация всех полей форм
- Улучшенная обработка ошибок
- Более информативные сообщения об ошибках
- Цветные уведомления о смене статуса заявки
- Исправление отображения списков в форме редактирования заявки (device_types, device_brands)
- Улучшенная навигация (ссылки на историю устройства из таблицы заявок)
- Удаление дубля поиска в списке клиентов
- Сортировка клиентов по умолчанию (новые клиенты сверху)

Подробнее: [SECURITY.md](SECURITY.md)

## Актуализация (2026-02-23)

- Удалены отдельные поля ссылок из `/settings` (`portal_public_url`, `review_url`, `director_contact_url`); ссылки и тексты клиентских писем настраиваются в email-шаблонах.
- Добавлены и применены миграции `051`, `052`, `053` (настройки директора, очистка устаревших колонок, защита от дублей `salary_accruals`).
- В `/all_orders` в dropdown кнопки `Статус` скрыты архивные статусы.
- Исправлена логика начисления зарплаты при повторном закрытии заявки: повторный переход в зарплатный статус не создает дублей.
- Выполнена дедупликация исторических начислений и добавлен скрипт `scripts/dedupe_salary_accruals.py`.

Подробно: [docs/OSS_RELEASE_WORKFLOW.md](docs/OSS_RELEASE_WORKFLOW.md)

## Лицензия

[Укажите лицензию]

## Авторы

Команда проекта Nika Service CRM.

## Поддержка

Для вопросов и поддержки используйте Issues в GitHub-репозитории.

---

**Версия документа:** 2.4  
**Последнее обновление:** 2026-03-02  
*Полная документация: руководство пользователя, API, план скриптов, маршруты, шаблоны, сервисы, модели, скрипты — по результатам сканирования кодовой базы.*

