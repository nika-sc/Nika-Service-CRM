"""
Миграция 003: Система склада.

Расширяет структуру БД для работы со складом:
- Обновляет таблицу parts (добавляет purchase_price, переименовывает price в retail_price)
- Создает таблицу purchases (закупки)
- Создает таблицу purchase_items (позиции закупок)
- Создает таблицу stock_movements (движения товаров)
- Добавляет индексы для оптимизации
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 003_warehouse: создание системы склада")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Обновление таблицы parts
        # Добавляем purchase_price
        try:
            cursor.execute('''
                ALTER TABLE parts 
                ADD COLUMN purchase_price DECIMAL(10, 2) DEFAULT 0.00
            ''')
            logger.info("Добавлена колонка purchase_price в таблицу parts")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' not in str(e).lower():
                raise
            logger.info("Колонка purchase_price уже существует")
        
        # Переименовываем price в retail_price
        # SQLite не поддерживает ALTER TABLE RENAME COLUMN напрямую,
        # поэтому используем обходной путь
        try:
            # Проверяем, существует ли уже retail_price
            cursor.execute("PRAGMA table_info(parts)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'retail_price' not in columns and 'price' in columns:
                # Создаем новую таблицу с правильной структурой
                cursor.execute('''
                    CREATE TABLE parts_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        part_number TEXT,
                        description TEXT,
                        retail_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                        purchase_price DECIMAL(10, 2) DEFAULT 0.00,
                        stock_quantity INTEGER NOT NULL DEFAULT 0,
                        min_quantity INTEGER NOT NULL DEFAULT 0,
                        category TEXT,
                        supplier TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Копируем данные
                cursor.execute('''
                    INSERT INTO parts_new 
                    (id, name, part_number, description, retail_price, purchase_price, 
                     stock_quantity, min_quantity, category, supplier, created_at, updated_at)
                    SELECT 
                        id, name, part_number, description, price, 
                        COALESCE(purchase_price, 0.00),
                        stock_quantity, min_quantity, category, supplier, created_at, updated_at
                    FROM parts
                ''')
                
                # Удаляем старую таблицу
                cursor.execute('DROP TABLE parts')
                
                # Переименовываем новую таблицу
                cursor.execute('ALTER TABLE parts_new RENAME TO parts')
                
                # Восстанавливаем индексы
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_name ON parts(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_part_number ON parts(part_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_category ON parts(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_stock_quantity ON parts(stock_quantity)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_category_stock ON parts(category, stock_quantity)')
                
                logger.info("Колонка price переименована в retail_price")
            elif 'retail_price' in columns:
                logger.info("Колонка retail_price уже существует")
        except Exception as e:
            logger.warning(f"Ошибка при переименовании колонки price: {e}")
        
        # 2. Создание таблицы purchases (закупки)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_id INTEGER,
                supplier_name TEXT,
                purchase_date DATE NOT NULL,
                total_amount DECIMAL(10, 2) DEFAULT 0.00,
                status TEXT NOT NULL DEFAULT 'draft',
                notes TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_supplier_id ON purchases(supplier_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_purchase_date ON purchases(purchase_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_created_at ON purchases(created_at)')
        
        # 3. Создание таблицы purchase_items (позиции закупок)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS purchase_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                purchase_price DECIMAL(10, 2) NOT NULL,
                total_price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES parts(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchase_items_purchase_id ON purchase_items(purchase_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchase_items_part_id ON purchase_items(part_id)')
        
        # 4. Создание таблицы stock_movements (движения товаров)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER NOT NULL,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                reference_id INTEGER,
                reference_type TEXT,
                created_by INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_id) REFERENCES parts(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_movements_part_id ON stock_movements(part_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_movements_movement_type ON stock_movements(movement_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_movements_reference ON stock_movements(reference_type, reference_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_movements_created_at ON stock_movements(created_at)')
        
        conn.commit()
        logger.info("Миграция 003_warehouse успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 003_warehouse: удаление таблиц склада")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицы в обратном порядке зависимостей
        tables = [
            'stock_movements',
            'purchase_items',
            'purchases'
        ]
        
        for table in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
                logger.info(f"Таблица {table} удалена")
            except Exception as e:
                logger.warning(f"Не удалось удалить таблицу {table}: {e}")
        
        # Откат изменений в таблице parts
        # Удаляем purchase_price (если существует)
        try:
            # SQLite не поддерживает DROP COLUMN напрямую
            # Нужно пересоздать таблицу без этой колонки
            cursor.execute("PRAGMA table_info(parts)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'purchase_price' in columns or 'retail_price' in columns:
                # Создаем таблицу со старой структурой
                cursor.execute('''
                    CREATE TABLE parts_old (
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
                
                # Копируем данные (используем retail_price как price)
                if 'retail_price' in columns:
                    cursor.execute('''
                        INSERT INTO parts_old 
                        (id, name, part_number, description, price, 
                         stock_quantity, min_quantity, category, supplier, created_at, updated_at)
                        SELECT 
                            id, name, part_number, description, retail_price,
                            stock_quantity, min_quantity, category, supplier, created_at, updated_at
                        FROM parts
                    ''')
                else:
                    cursor.execute('''
                        INSERT INTO parts_old 
                        (id, name, part_number, description, price, 
                         stock_quantity, min_quantity, category, supplier, created_at, updated_at)
                        SELECT 
                            id, name, part_number, description, price,
                            stock_quantity, min_quantity, category, supplier, created_at, updated_at
                        FROM parts
                    ''')
                
                # Удаляем старую таблицу
                cursor.execute('DROP TABLE parts')
                
                # Переименовываем
                cursor.execute('ALTER TABLE parts_old RENAME TO parts')
                
                # Восстанавливаем индексы
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_name ON parts(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_part_number ON parts(part_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_category ON parts(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_stock_quantity ON parts(stock_quantity)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_category_stock ON parts(category, stock_quantity)')
                
                logger.info("Таблица parts откачена к исходному состоянию")
        except Exception as e:
            logger.warning(f"Ошибка при откате таблицы parts: {e}")
        
        conn.commit()
        logger.info("Миграция 003_warehouse откачена")

