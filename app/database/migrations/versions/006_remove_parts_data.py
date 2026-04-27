"""
Миграция 006: Удаление данных запчастей.

Удаляет:
- Таблицу order_parts (проводки запчастей в заявках)
- Движения типа 'purchase' из stock_movements
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 006_remove_parts_data: удаление данных запчастей")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Удаляем движения типа 'purchase' из stock_movements
        try:
            cursor.execute("SELECT COUNT(*) FROM stock_movements WHERE movement_type = 'purchase'")
            count = cursor.fetchone()[0]
            logger.info(f"Найдено движений типа 'purchase': {count}")
            
            cursor.execute("DELETE FROM stock_movements WHERE movement_type = 'purchase'")
            deleted_count = cursor.rowcount
            logger.info(f"Удалено движений типа 'purchase': {deleted_count}")
        except Exception as e:
            logger.warning(f"Ошибка при удалении движений purchase: {e}")
        
        # 2. Удаляем таблицу order_parts
        try:
            # Проверяем существование таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_parts'")
            if cursor.fetchone():
                # Удаляем индексы
                cursor.execute("DROP INDEX IF EXISTS idx_order_parts_order_id")
                cursor.execute("DROP INDEX IF EXISTS idx_order_parts_part_id")
                
                # Удаляем таблицу
                cursor.execute("DROP TABLE IF EXISTS order_parts")
                logger.info("Таблица order_parts удалена")
            else:
                logger.info("Таблица order_parts не существует")
        except Exception as e:
            logger.warning(f"Ошибка при удалении таблицы order_parts: {e}")
        
        conn.commit()
        logger.info("Миграция 006_remove_parts_data успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 006_remove_parts_data: восстановление таблицы order_parts")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Восстанавливаем таблицу order_parts (если нужно)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_parts'")
            if not cursor.fetchone():
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS order_parts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        part_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL DEFAULT 1,
                        price DECIMAL(10, 2) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                        FOREIGN KEY (part_id) REFERENCES parts(id),
                        UNIQUE(order_id, part_id)
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_parts_order_id ON order_parts(order_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_parts_part_id ON order_parts(part_id)')
                logger.info("Таблица order_parts восстановлена")
        except Exception as e:
            logger.warning(f"Ошибка при восстановлении таблицы order_parts: {e}")
        
        # Движения purchase не восстанавливаем (данные потеряны)
        
        conn.commit()
        logger.info("Миграция 006_remove_parts_data откачена")

