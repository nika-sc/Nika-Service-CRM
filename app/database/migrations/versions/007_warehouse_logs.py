"""
Миграция 007: Логирование операций со складом.

Создает таблицу warehouse_logs для логирования всех операций:
- Создание товаров
- Удаление товаров
- Оприходование товаров
- Списание товаров
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 007_warehouse_logs: создание таблицы логов склада")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Создание таблицы warehouse_logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouse_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                part_id INTEGER,
                part_name TEXT,
                part_number TEXT,
                user_id INTEGER,
                username TEXT,
                quantity INTEGER,
                old_value TEXT,
                new_value TEXT,
                notes TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_id) REFERENCES parts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Создание индексов для оптимизации
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_warehouse_logs_operation_type ON warehouse_logs(operation_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_warehouse_logs_part_id ON warehouse_logs(part_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_warehouse_logs_user_id ON warehouse_logs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_warehouse_logs_created_at ON warehouse_logs(created_at)')
        
        conn.commit()
        logger.info("Миграция 007_warehouse_logs успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 007_warehouse_logs: удаление таблицы логов")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаление индексов
        try:
            cursor.execute('DROP INDEX IF EXISTS idx_warehouse_logs_operation_type')
            cursor.execute('DROP INDEX IF EXISTS idx_warehouse_logs_part_id')
            cursor.execute('DROP INDEX IF EXISTS idx_warehouse_logs_user_id')
            cursor.execute('DROP INDEX IF EXISTS idx_warehouse_logs_created_at')
            logger.info("Индексы удалены")
        except Exception as e:
            logger.warning(f"Не удалось удалить индексы: {e}")
        
        # Удаление таблицы
        try:
            cursor.execute('DROP TABLE IF EXISTS warehouse_logs')
            logger.info("Таблица warehouse_logs удалена")
        except Exception as e:
            logger.warning(f"Не удалось удалить таблицу warehouse_logs: {e}")
        
        conn.commit()
        logger.info("Миграция 007_warehouse_logs откачена")

