"""
Миграция 001: Базовая структура базы данных.

Создает все основные таблицы, справочники и индексы.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 001_initial: создание базовой структуры БД")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Справочники (создаются первыми, так как на них ссылаются другие таблицы)
        
        # Типы устройств
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_types_sort_order ON device_types(sort_order)')
        
        # Бренды устройств
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device_brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_device_brands_sort_order ON device_brands(sort_order)')
        
        # Менеджеры
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Мастера
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Симптомы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS symptoms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symptoms_sort_order ON symptoms(sort_order)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symptoms_name ON symptoms(name)')
        
        # Теги внешнего вида
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS appearance_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appearance_tags_sort_order ON appearance_tags(sort_order)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_appearance_tags_name ON appearance_tags(name)')
        
        # Статусы заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_statuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#007bff',
                is_default INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_statuses_code ON order_statuses(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_statuses_sort_order ON order_statuses(sort_order)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_statuses_is_default ON order_statuses(is_default)')
        
        # Основные таблицы
        
        # Клиенты
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(phone)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)')
        
        # Устройства
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                device_type_id INTEGER NOT NULL,
                device_brand_id INTEGER NOT NULL,
                serial_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (device_type_id) REFERENCES device_types(id),
                FOREIGN KEY (device_brand_id) REFERENCES device_brands(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_customer_id ON devices(customer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_device_type_id ON devices(device_type_id)')
        
        # Заявки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                device_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                manager_id INTEGER NOT NULL,
                master_id INTEGER,
                status_id INTEGER,
                status TEXT DEFAULT 'new',
                prepayment TEXT NOT NULL DEFAULT '0',
                password TEXT,
                appearance TEXT,
                comment TEXT,
                symptom_tags TEXT,
                hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (manager_id) REFERENCES managers(id),
                FOREIGN KEY (master_id) REFERENCES masters(id),
                FOREIGN KEY (status_id) REFERENCES order_statuses(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_device_id ON orders(device_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_manager_id ON orders(manager_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_master_id ON orders(master_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status_id ON orders(status_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_hidden ON orders(hidden)')
        
        # Комментарии к заявкам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                author_name TEXT NOT NULL,
                comment_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_comments_order_id ON order_comments(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_comments_created_at ON order_comments(created_at)')
        
        # История видимости заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_visibility_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                hidden INTEGER NOT NULL,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_visibility_history_order_id ON order_visibility_history(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_visibility_history_changed_at ON order_visibility_history(changed_at)')
        
        # История статусов заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                old_status_id INTEGER,
                new_status_id INTEGER NOT NULL,
                changed_by INTEGER,
                changed_by_username TEXT,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (old_status_id) REFERENCES order_statuses(id),
                FOREIGN KEY (new_status_id) REFERENCES order_statuses(id),
                FOREIGN KEY (changed_by) REFERENCES users(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_status_history_order_id ON order_status_history(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_status_history_created_at ON order_status_history(created_at)')
        
        # Услуги
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                is_default INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_services_sort_order ON services(sort_order)')
        
        # Услуги заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id),
                UNIQUE(order_id, service_id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_services_order_id ON order_services(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_services_service_id ON order_services(service_id)')
        
        # Запчасти
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                part_number TEXT,
                description TEXT,
                price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                min_quantity INTEGER NOT NULL DEFAULT 0,
                category TEXT,
                supplier TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_name ON parts(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_part_number ON parts(part_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_category ON parts(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_stock_quantity ON parts(stock_quantity)')
        
        # Запчасти заявок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE RESTRICT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_parts_order_id ON order_parts(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_parts_part_id ON order_parts(part_id)')
        
        # Оплаты
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                payment_type TEXT NOT NULL,
                payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                created_by_username TEXT,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_payment_type ON payments(payment_type)')
        
        # Системные таблицы
        
        # Пользователи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)')
        
        # Общие настройки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS general_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                org_name TEXT,
                phone TEXT,
                address TEXT,
                inn TEXT,
                ogrn TEXT,
                logo_url TEXT,
                currency TEXT DEFAULT 'RUB',
                country TEXT DEFAULT 'Россия',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Шаблоны печати
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS print_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                template_type TEXT NOT NULL DEFAULT 'customer',
                html_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_print_templates_template_type ON print_templates(template_type)')
        
        # Логи действий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action_type TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_action_logs_user_id ON action_logs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_action_logs_entity ON action_logs(entity_type, entity_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_action_logs_created_at ON action_logs(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_action_logs_action_type ON action_logs(action_type)')
        
        conn.commit()
        logger.info("Миграция 001_initial успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 001_initial: удаление всех таблиц")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицы в обратном порядке зависимостей
        tables = [
            'action_logs',
            'print_templates',
            'general_settings',
            'payments',
            'order_parts',
            'order_services',
            'parts',
            'services',
            'order_status_history',
            'order_visibility_history',
            'order_comments',
            'orders',
            'devices',
            'customers',
            'order_statuses',
            'appearance_tags',
            'symptoms',
            'masters',
            'managers',
            'device_brands',
            'device_types',
            'users'
        ]
        
        for table in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
                logger.info(f"Таблица {table} удалена")
            except Exception as e:
                logger.warning(f"Не удалось удалить таблицу {table}: {e}")
        
        conn.commit()
        logger.info("Миграция 001_initial откачена")

