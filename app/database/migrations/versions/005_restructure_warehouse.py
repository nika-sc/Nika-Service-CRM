"""
Миграция 005: Реструктуризация склада.

Расширяет структуру БД для новой системы управления товарами:
- Добавляет поля в parts: unit, warranty_days, is_deleted, comment
- Создает таблицу part_categories для управления категориями товаров
- Добавляет индексы для оптимизации
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 005_restructure_warehouse: реструктуризация склада")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Добавление новых полей в таблицу parts
        try:
            # Проверяем текущую структуру таблицы
            cursor.execute("PRAGMA table_info(parts)")
            columns = {col[1]: col for col in cursor.fetchall()}
            
            # Добавляем unit (единица измерения)
            if 'unit' not in columns:
                cursor.execute('''
                    ALTER TABLE parts 
                    ADD COLUMN unit TEXT DEFAULT 'шт'
                ''')
                logger.info("Добавлена колонка unit в таблицу parts")
            else:
                logger.info("Колонка unit уже существует")
            
            # Добавляем warranty_days (гарантия в днях)
            if 'warranty_days' not in columns:
                cursor.execute('''
                    ALTER TABLE parts 
                    ADD COLUMN warranty_days INTEGER
                ''')
                logger.info("Добавлена колонка warranty_days в таблицу parts")
            else:
                logger.info("Колонка warranty_days уже существует")
            
            # Добавляем is_deleted (мягкое удаление)
            if 'is_deleted' not in columns:
                cursor.execute('''
                    ALTER TABLE parts 
                    ADD COLUMN is_deleted INTEGER DEFAULT 0
                ''')
                logger.info("Добавлена колонка is_deleted в таблицу parts")
            else:
                logger.info("Колонка is_deleted уже существует")
            
            # Добавляем comment (комментарий)
            if 'comment' not in columns:
                cursor.execute('''
                    ALTER TABLE parts 
                    ADD COLUMN comment TEXT
                ''')
                logger.info("Добавлена колонка comment в таблицу parts")
            else:
                logger.info("Колонка comment уже существует")
            
            # Добавляем индексы для новых полей
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_is_deleted ON parts(is_deleted)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_unit ON parts(unit)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_parts_category_deleted ON parts(category, is_deleted)')
            
        except sqlite3.OperationalError as e:
            logger.error(f"Ошибка при добавлении полей в parts: {e}")
            raise
        
        # 2. Создание таблицы part_categories (категории товаров)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS part_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_part_categories_name ON part_categories(name)')
        logger.info("Таблица part_categories создана")
        
        # 3. Миграция существующих категорий из parts в part_categories
        try:
            # Получаем уникальные категории из parts
            cursor.execute('''
                SELECT DISTINCT category 
                FROM parts 
                WHERE category IS NOT NULL AND category != ''
            ''')
            existing_categories = [row[0] for row in cursor.fetchall()]
            
            # Добавляем категории в part_categories, если их там еще нет
            for category_name in existing_categories:
                cursor.execute('''
                    INSERT OR IGNORE INTO part_categories (name)
                    VALUES (?)
                ''', (category_name,))
            
            if existing_categories:
                logger.info(f"Мигрировано {len(existing_categories)} категорий в part_categories")
        except Exception as e:
            logger.warning(f"Ошибка при миграции категорий: {e}")
        
        conn.commit()
        logger.info("Миграция 005_restructure_warehouse успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 005_restructure_warehouse: удаление новых полей и таблицы")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицу part_categories
        try:
            cursor.execute('DROP TABLE IF EXISTS part_categories')
            logger.info("Таблица part_categories удалена")
        except Exception as e:
            logger.warning(f"Не удалось удалить таблицу part_categories: {e}")
        
        # Удаляем индексы
        try:
            cursor.execute('DROP INDEX IF EXISTS idx_parts_is_deleted')
            cursor.execute('DROP INDEX IF EXISTS idx_parts_unit')
            cursor.execute('DROP INDEX IF EXISTS idx_parts_category_deleted')
            logger.info("Индексы удалены")
        except Exception as e:
            logger.warning(f"Не удалось удалить индексы: {e}")
        
        # SQLite не поддерживает DROP COLUMN напрямую
        # Для отката нужно пересоздать таблицу без новых колонок
        try:
            cursor.execute("PRAGMA table_info(parts)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Проверяем, есть ли новые колонки для удаления
            new_columns = ['unit', 'warranty_days', 'is_deleted', 'comment']
            has_new_columns = any(col in columns for col in new_columns)
            
            if has_new_columns:
                # Создаем таблицу со старой структурой (без новых полей)
                cursor.execute('''
                    CREATE TABLE parts_old (
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
                
                # Копируем данные (исключаем новые поля)
                cursor.execute('''
                    INSERT INTO parts_old 
                    (id, name, part_number, description, retail_price, purchase_price,
                     stock_quantity, min_quantity, category, supplier, created_at, updated_at)
                    SELECT 
                        id, name, part_number, description, retail_price, purchase_price,
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
                
                logger.info("Таблица parts откачена к состоянию без новых полей")
        except Exception as e:
            logger.warning(f"Ошибка при откате таблицы parts: {e}")
        
        conn.commit()
        logger.info("Миграция 005_restructure_warehouse откачена")

