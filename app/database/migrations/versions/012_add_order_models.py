"""
Миграция 012: Добавление таблицы order_models и поля model в таблицу orders.

Создает таблицу для хранения моделей устройств с автопоиском и добавляет поле model в таблицу orders.
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 012_add_order_models: создание таблицы order_models и добавление поля model в orders")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Создаем таблицу order_models
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_models_name ON order_models(name)')
            logger.info("Создана таблица order_models")
        except sqlite3.OperationalError as e:
            if 'already exists' not in str(e).lower():
                raise
            logger.info("Таблица order_models уже существует")
        
        # Добавляем поле model в таблицу orders
        try:
            cursor.execute('''
                ALTER TABLE orders 
                ADD COLUMN model TEXT
            ''')
            logger.info("Добавлена колонка model в таблицу orders")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' not in str(e).lower():
                raise
            logger.info("Колонка model уже существует")
        
        conn.commit()
        logger.info("Миграция 012_add_order_models успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 012_add_order_models: удаление таблицы order_models и поля model из orders")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицу order_models
        try:
            cursor.execute('DROP TABLE IF EXISTS order_models')
            logger.info("Таблица order_models удалена")
        except sqlite3.OperationalError as e:
            logger.warning(f"Не удалось удалить таблицу order_models: {e}")
        
        # SQLite не поддерживает DROP COLUMN напрямую
        # Для отката нужно пересоздать таблицу без этой колонки
        logger.warning("Откат поля model из таблицы orders не поддерживается (SQLite ограничения)")
        logger.warning("Для отката необходимо вручную пересоздать таблицу orders")
        
        conn.commit()
        logger.info("Миграция 012_add_order_models откачена")

