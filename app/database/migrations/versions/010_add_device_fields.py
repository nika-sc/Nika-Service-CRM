"""
Миграция 010: Добавление дополнительных полей в таблицу devices.

Добавляет поля для хранения пароля, типичных неисправностей и внешнего вида устройства.
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 010_add_device_fields: добавление полей в таблицу devices")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Добавляем поле password
        try:
            cursor.execute('''
                ALTER TABLE devices 
                ADD COLUMN password TEXT
            ''')
            logger.info("Добавлена колонка password в таблицу devices")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' not in str(e).lower():
                raise
            logger.info("Колонка password уже существует")
        
        # Добавляем поле symptom_tags
        try:
            cursor.execute('''
                ALTER TABLE devices 
                ADD COLUMN symptom_tags TEXT
            ''')
            logger.info("Добавлена колонка symptom_tags в таблицу devices")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' not in str(e).lower():
                raise
            logger.info("Колонка symptom_tags уже существует")
        
        # Добавляем поле appearance_tags
        try:
            cursor.execute('''
                ALTER TABLE devices 
                ADD COLUMN appearance_tags TEXT
            ''')
            logger.info("Добавлена колонка appearance_tags в таблицу devices")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' not in str(e).lower():
                raise
            logger.info("Колонка appearance_tags уже существует")
        
        conn.commit()
        logger.info("Миграция 010_add_device_fields успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 010_add_device_fields: удаление полей из таблицы devices")
    
    # SQLite не поддерживает DROP COLUMN напрямую
    # Для отката нужно пересоздать таблицу без этих колонок
    # Это сложная операция, поэтому просто логируем предупреждение
    logger.warning("Откат миграции 010_add_device_fields не поддерживается (SQLite ограничения)")
    logger.warning("Для отката необходимо вручную пересоздать таблицу devices")

