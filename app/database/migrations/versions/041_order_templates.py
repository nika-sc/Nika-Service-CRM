"""
Миграция 041: Система шаблонов заявок.

Создает:
1. Таблицу order_templates для шаблонов заявок
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
    logger.info("Применение миграции 041_order_templates")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Создаем таблицу order_templates
        if not _table_exists(cursor, 'order_templates'):
            logger.info("Создание таблицы order_templates...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    template_data TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    is_public INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_order_templates_created_by 
                ON order_templates(created_by)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_order_templates_is_public 
                ON order_templates(is_public)
            ''')
            
            logger.info("Таблица order_templates создана")
        else:
            logger.info("Таблица order_templates уже существует, пропускаем")
        
        conn.commit()
        logger.info("Миграция 041_order_templates успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 041_order_templates")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if _table_exists(cursor, 'order_templates'):
            logger.info("Удаление таблицы order_templates...")
            cursor.execute('DROP TABLE IF EXISTS order_templates')
            logger.info("Таблица order_templates удалена")
        
        conn.commit()
        logger.info("Миграция 041_order_templates откачена")
