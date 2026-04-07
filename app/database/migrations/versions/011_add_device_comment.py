"""
Миграция 011: Добавление поля comment в таблицу devices.

Добавляет поле для хранения комментария к устройству (виден только сервисному центру).
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 011_add_device_comment: добавление поля comment в таблицу devices")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Добавляем поле comment
        try:
            cursor.execute('''
                ALTER TABLE devices 
                ADD COLUMN comment TEXT
            ''')
            logger.info("Добавлена колонка comment в таблицу devices")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' not in str(e).lower():
                raise
            logger.info("Колонка comment уже существует")
        
        conn.commit()
        logger.info("Миграция 011_add_device_comment успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 011_add_device_comment: удаление поля comment из таблицы devices")
    
    # SQLite не поддерживает DROP COLUMN напрямую
    # Для отката нужно пересоздать таблицу без этой колонки
    # Это сложная операция, поэтому просто логируем предупреждение
    logger.warning("Откат миграции 011_add_device_comment не поддерживается (SQLite ограничения)")
    logger.warning("Для отката необходимо вручную пересоздать таблицу devices")


