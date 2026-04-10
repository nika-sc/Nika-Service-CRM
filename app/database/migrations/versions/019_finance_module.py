"""
Миграция 019: Финансовый модуль
- Статьи доходов и расходов
- Кассовые операции
- Продажи в магазине (без заявки)
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up() -> None:
    """Применение миграции."""
    logger.info("Применение миграции 019: Финансовый модуль")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Статьи доходов и расходов (категории транзакций)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                description TEXT,
                color TEXT DEFAULT '#6c757d',
                is_system INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Добавляем системные статьи
        system_categories = [
            # Доходы
            ('Оплата услуг', 'income', 'Оплата за ремонтные работы', '#28a745', 1),
            ('Продажа товаров', 'income', 'Продажа запчастей и аксессуаров', '#17a2b8', 1),
            ('Предоплата', 'income', 'Предоплата от клиента', '#ffc107', 1),
            ('Прочий доход', 'income', 'Другие поступления', '#6c757d', 0),
            # Расходы
            ('Закупка товаров', 'expense', 'Закупка запчастей и товаров', '#dc3545', 1),
            ('Зарплата', 'expense', 'Выплата заработной платы', '#fd7e14', 1),
            ('Аренда', 'expense', 'Арендная плата', '#6610f2', 0),
            ('Коммунальные', 'expense', 'Коммунальные платежи', '#20c997', 0),
            ('Реклама', 'expense', 'Расходы на рекламу', '#e83e8c', 0),
            ('Прочий расход', 'expense', 'Другие расходы', '#6c757d', 0),
        ]
        
        for i, (name, cat_type, desc, color, is_system) in enumerate(system_categories, 1):
            cursor.execute('''
                INSERT OR IGNORE INTO transaction_categories (name, type, description, color, is_system, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, cat_type, desc, color, is_system, i))
        
        # 2. Кассовые операции (транзакции)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cash_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('income', 'expense')),
                payment_method TEXT DEFAULT 'cash' CHECK(payment_method IN ('cash', 'card', 'transfer', 'other')),
                description TEXT,
                
                order_id INTEGER,
                payment_id INTEGER,
                shop_sale_id INTEGER,
                
                transaction_date DATE NOT NULL DEFAULT (DATE('now')),
                created_by_id INTEGER,
                created_by_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (category_id) REFERENCES transaction_categories(id),
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id),
                FOREIGN KEY (created_by_id) REFERENCES users(id)
            )
        ''')
        
        # 3. Продажи в магазине (без заявки)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                customer_id INTEGER,
                customer_name TEXT,
                customer_phone TEXT,
                
                manager_id INTEGER,
                master_id INTEGER,
                
                total_amount REAL NOT NULL DEFAULT 0,
                discount REAL DEFAULT 0,
                final_amount REAL NOT NULL DEFAULT 0,
                paid_amount REAL DEFAULT 0,
                payment_method TEXT DEFAULT 'cash',
                
                comment TEXT,
                
                sale_date DATE NOT NULL DEFAULT (DATE('now')),
                created_by_id INTEGER,
                created_by_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (manager_id) REFERENCES users(id),
                FOREIGN KEY (master_id) REFERENCES users(id),
                FOREIGN KEY (created_by_id) REFERENCES users(id)
            )
        ''')
        
        # 4. Позиции продажи в магазине
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop_sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_sale_id INTEGER NOT NULL,
                
                item_type TEXT NOT NULL CHECK(item_type IN ('service', 'part')),
                
                service_id INTEGER,
                service_name TEXT,
                
                part_id INTEGER,
                part_name TEXT,
                part_sku TEXT,
                
                quantity INTEGER NOT NULL DEFAULT 1,
                price REAL NOT NULL,
                purchase_price REAL DEFAULT 0,
                total REAL NOT NULL,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (shop_sale_id) REFERENCES shop_sales(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id),
                FOREIGN KEY (part_id) REFERENCES parts(id)
            )
        ''')
        
        # 5. Индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_transactions_date ON cash_transactions(transaction_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_transactions_type ON cash_transactions(transaction_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_transactions_category ON cash_transactions(category_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cash_transactions_order ON cash_transactions(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shop_sales_date ON shop_sales(sale_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shop_sales_customer ON shop_sales(customer_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_shop_sale_items_sale ON shop_sale_items(shop_sale_id)')
        
        conn.commit()
        logger.info("Миграция 019: Финансовый модуль применена успешно")


def down() -> None:
    """Откат миграции."""
    logger.info("Откат миграции 019: Финансовый модуль")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('DROP TABLE IF EXISTS shop_sale_items')
        cursor.execute('DROP TABLE IF EXISTS shop_sales')
        cursor.execute('DROP TABLE IF EXISTS cash_transactions')
        cursor.execute('DROP TABLE IF EXISTS transaction_categories')
        
        conn.commit()
        logger.info("Миграция 019: Финансовый модуль откачена")
