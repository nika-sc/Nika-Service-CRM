"""
Миграция 008: Добавление поддержки подкатегорий.

Добавляет поле parent_id в таблицу part_categories для создания иерархии категорий.
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 008_add_subcategories: добавление поддержки подкатегорий")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем текущую структуру таблицы
        cursor.execute("PRAGMA table_info(part_categories)")
        columns = {col[1]: col for col in cursor.fetchall()}
        
        # Добавляем поле parent_id для поддержки иерархии
        if 'parent_id' not in columns:
            cursor.execute('''
                ALTER TABLE part_categories 
                ADD COLUMN parent_id INTEGER
            ''')
            logger.info("Добавлена колонка parent_id в таблицу part_categories")
        else:
            logger.info("Колонка parent_id уже существует")
        
        # Добавляем индекс для оптимизации
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_part_categories_parent_id ON part_categories(parent_id)')
        
        # Добавляем внешний ключ (SQLite поддерживает это через триггеры, но для простоты просто создаем индекс)
        # FOREIGN KEY (parent_id) REFERENCES part_categories(id)
        
        conn.commit()
        logger.info("Миграция 008_add_subcategories успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 008_add_subcategories: удаление поддержки подкатегорий")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем индекс
        try:
            cursor.execute('DROP INDEX IF EXISTS idx_part_categories_parent_id')
            logger.info("Индекс удален")
        except Exception as e:
            logger.warning(f"Не удалось удалить индекс: {e}")
        
        # SQLite не поддерживает DROP COLUMN напрямую
        # Для отката нужно пересоздать таблицу без parent_id
        try:
            cursor.execute("PRAGMA table_info(part_categories)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'parent_id' in columns:
                # Создаем таблицу без parent_id
                cursor.execute('''
                    CREATE TABLE part_categories_old (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Копируем данные (исключаем parent_id)
                cursor.execute('''
                    INSERT INTO part_categories_old 
                    (id, name, description, created_at, updated_at)
                    SELECT 
                        id, name, description, created_at, updated_at
                    FROM part_categories
                ''')
                
                # Удаляем старую таблицу
                cursor.execute('DROP TABLE part_categories')
                
                # Переименовываем
                cursor.execute('ALTER TABLE part_categories_old RENAME TO part_categories')
                
                # Восстанавливаем индексы
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_part_categories_name ON part_categories(name)')
                
                logger.info("Таблица part_categories откачена к состоянию без parent_id")
        except Exception as e:
            logger.warning(f"Ошибка при откате таблицы part_categories: {e}")
        
        conn.commit()
        logger.info("Миграция 008_add_subcategories откачена")

