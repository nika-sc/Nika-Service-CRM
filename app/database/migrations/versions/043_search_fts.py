"""
Миграция 043: FTS индексы для полнотекстового поиска.

Создает виртуальные таблицы FTS для полнотекстового поиска.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _table_exists(cursor, table_name: str) -> bool:
    """Проверяет существование таблицы."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 043_search_fts")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # FTS таблица для заявок
        if not _table_exists(cursor, 'orders_fts'):
            logger.info("Создание FTS таблицы orders_fts...")
            cursor.execute('''
                CREATE VIRTUAL TABLE orders_fts USING fts5(
                    order_id,
                    client_name,
                    phone,
                    email,
                    serial_number,
                    device_type,
                    device_brand,
                    comment,
                    symptom_tags,
                    appearance,
                    content='orders',
                    content_rowid='id'
                )
            ''')
            
            # Заполняем FTS таблицу данными из orders
            cursor.execute('''
                INSERT INTO orders_fts(rowid, order_id, client_name, phone, email, serial_number, device_type, device_brand, comment, symptom_tags, appearance)
                SELECT 
                    o.id,
                    o.order_id,
                    c.name,
                    c.phone,
                    c.email,
                    d.serial_number,
                    dt.name,
                    db.name,
                    o.comment,
                    o.symptom_tags,
                    o.appearance
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN devices d ON d.id = o.device_id
                LEFT JOIN device_types dt ON dt.id = d.device_type_id
                LEFT JOIN device_brands db ON db.id = d.device_brand_id
            ''')
            
            logger.info("FTS таблица orders_fts создана")
        else:
            logger.info("FTS таблица orders_fts уже существует, пропускаем")
        
        # FTS таблица для клиентов
        if not _table_exists(cursor, 'customers_fts'):
            logger.info("Создание FTS таблицы customers_fts...")
            cursor.execute('''
                CREATE VIRTUAL TABLE customers_fts USING fts5(
                    name,
                    phone,
                    email,
                    content='customers',
                    content_rowid='id'
                )
            ''')
            
            # Заполняем FTS таблицу данными из customers
            cursor.execute('''
                INSERT INTO customers_fts(rowid, name, phone, email)
                SELECT id, name, phone, email FROM customers
            ''')
            
            logger.info("FTS таблица customers_fts создана")
        else:
            logger.info("FTS таблица customers_fts уже существует, пропускаем")
        
        # FTS таблица для товаров
        if not _table_exists(cursor, 'parts_fts'):
            logger.info("Создание FTS таблицы parts_fts...")
            cursor.execute('''
                CREATE VIRTUAL TABLE parts_fts USING fts5(
                    name,
                    part_number,
                    description,
                    content='parts',
                    content_rowid='id'
                )
            ''')
            
            # Заполняем FTS таблицу данными из parts
            cursor.execute('''
                INSERT INTO parts_fts(rowid, name, part_number, description)
                SELECT id, name, COALESCE(part_number, ''), COALESCE(description, '') FROM parts
            ''')
            
            logger.info("FTS таблица parts_fts создана")
        else:
            logger.info("FTS таблица parts_fts уже существует, пропускаем")
        
        # Триггеры для автоматического обновления FTS при изменении данных
        # Для orders
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS orders_fts_insert AFTER INSERT ON orders BEGIN
                INSERT INTO orders_fts(rowid, order_id, client_name, phone, email, serial_number, device_type, device_brand, comment, symptom_tags, appearance)
                SELECT 
                    o.id,
                    o.order_id,
                    c.name,
                    c.phone,
                    c.email,
                    d.serial_number,
                    dt.name,
                    db.name,
                    o.comment,
                    o.symptom_tags,
                    o.appearance
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN devices d ON d.id = o.device_id
                LEFT JOIN device_types dt ON dt.id = d.device_type_id
                LEFT JOIN device_brands db ON db.id = d.device_brand_id
                WHERE o.id = NEW.id;
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS orders_fts_update AFTER UPDATE ON orders BEGIN
                DELETE FROM orders_fts WHERE rowid = NEW.id;
                INSERT INTO orders_fts(rowid, order_id, client_name, phone, email, serial_number, device_type, device_brand, comment, symptom_tags, appearance)
                SELECT 
                    o.id,
                    o.order_id,
                    c.name,
                    c.phone,
                    c.email,
                    d.serial_number,
                    dt.name,
                    db.name,
                    o.comment,
                    o.symptom_tags,
                    o.appearance
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN devices d ON d.id = o.device_id
                LEFT JOIN device_types dt ON dt.id = d.device_type_id
                LEFT JOIN device_brands db ON db.id = d.device_brand_id
                WHERE o.id = NEW.id;
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS orders_fts_delete AFTER DELETE ON orders BEGIN
                DELETE FROM orders_fts WHERE rowid = OLD.id;
            END
        ''')
        
        # Для customers
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS customers_fts_insert AFTER INSERT ON customers BEGIN
                INSERT INTO customers_fts(rowid, name, phone, email)
                VALUES (NEW.id, NEW.name, NEW.phone, NEW.email);
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS customers_fts_update AFTER UPDATE ON customers BEGIN
                UPDATE customers_fts SET name = NEW.name, phone = NEW.phone, email = NEW.email WHERE rowid = NEW.id;
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS customers_fts_delete AFTER DELETE ON customers BEGIN
                DELETE FROM customers_fts WHERE rowid = OLD.id;
            END
        ''')
        
        # Для parts
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS parts_fts_insert AFTER INSERT ON parts BEGIN
                INSERT INTO parts_fts(rowid, name, part_number, description)
                VALUES (NEW.id, NEW.name, COALESCE(NEW.part_number, ''), COALESCE(NEW.description, ''));
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS parts_fts_update AFTER UPDATE ON parts BEGIN
                UPDATE parts_fts SET name = NEW.name, part_number = COALESCE(NEW.part_number, ''), description = COALESCE(NEW.description, '') WHERE rowid = NEW.id;
            END
        ''')
        
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS parts_fts_delete AFTER DELETE ON parts BEGIN
                DELETE FROM parts_fts WHERE rowid = OLD.id;
            END
        ''')
        
        conn.commit()
        logger.info("Миграция 043_search_fts успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 043_search_fts")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем триггеры
        triggers = [
            'orders_fts_insert', 'orders_fts_update', 'orders_fts_delete',
            'customers_fts_insert', 'customers_fts_update', 'customers_fts_delete',
            'parts_fts_insert', 'parts_fts_update', 'parts_fts_delete'
        ]
        
        for trigger in triggers:
            cursor.execute(f'DROP TRIGGER IF EXISTS {trigger}')
        
        # Удаляем FTS таблицы
        fts_tables = ['orders_fts', 'customers_fts', 'parts_fts']
        for table in fts_tables:
            if _table_exists(cursor, table):
                logger.info(f"Удаление FTS таблицы {table}...")
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
                logger.info(f"FTS таблица {table} удалена")
        
        conn.commit()
        logger.info("Миграция 043_search_fts откачена")
