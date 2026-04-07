"""
Миграция 009: Добавление category_id в warehouse_logs.

Добавляет поле category_id в таблицу warehouse_logs для логирования операций с категориями.
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 009_add_category_id_to_logs: добавление category_id в warehouse_logs")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем, существует ли колонка category_id
        try:
            cursor.execute("PRAGMA table_info(warehouse_logs)")
            columns = {col[1]: col for col in cursor.fetchall()}
            
            if 'category_id' not in columns:
                cursor.execute('''
                    ALTER TABLE warehouse_logs 
                    ADD COLUMN category_id INTEGER
                ''')
                logger.info("Добавлена колонка category_id в таблицу warehouse_logs")
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_warehouse_logs_category_id ON warehouse_logs(category_id)')
                logger.info("Добавлен индекс idx_warehouse_logs_category_id")
            else:
                logger.info("Колонка category_id уже существует")
        except sqlite3.OperationalError as e:
            logger.error(f"Ошибка при добавлении category_id в warehouse_logs: {e}")
            raise
        
        conn.commit()
        logger.info("Миграция 009_add_category_id_to_logs успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 009_add_category_id_to_logs: удаление category_id из warehouse_logs")
    
    # SQLite не поддерживает DROP COLUMN, поэтому просто удаляем индекс
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute('DROP INDEX IF EXISTS idx_warehouse_logs_category_id')
            logger.info("Индекс idx_warehouse_logs_category_id удален")
        except Exception as e:
            logger.warning(f"Не удалось удалить индекс: {e}")
        
        conn.commit()
        logger.info("Миграция 009_add_category_id_to_logs откачена (колонка category_id оставлена)")

