"""
Миграция 045: Добавление поля portal_password_changed в таблицу customers.

Добавляет флаг для отслеживания, менял ли клиент пароль портала после первого входа.
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Проверяет существование колонки в таблице."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 045_portal_password_change_flag: добавление поля portal_password_changed")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Добавляем поле portal_password_changed
        if not _column_exists(cursor, "customers", "portal_password_changed"):
            try:
                cursor.execute('''
                    ALTER TABLE customers 
                    ADD COLUMN portal_password_changed INTEGER DEFAULT 0
                ''')
                logger.info("Добавлена колонка portal_password_changed в таблицу customers")
            except sqlite3.OperationalError as e:
                if 'duplicate column name' not in str(e).lower():
                    raise
                logger.info("Колонка portal_password_changed уже существует")
        else:
            logger.info("Колонка portal_password_changed уже существует")
        
        conn.commit()
        logger.info("Миграция 045_portal_password_change_flag успешно применена")


def down():
    """Откатывает миграцию."""
    logger.info("Откат миграции 045_portal_password_change_flag: удаление поля portal_password_changed")
    
    # SQLite не поддерживает DROP COLUMN напрямую
    # Для отката потребуется пересоздание таблицы, что не рекомендуется
    logger.warning("Откат миграции 045 не поддерживается (SQLite ограничение)")
