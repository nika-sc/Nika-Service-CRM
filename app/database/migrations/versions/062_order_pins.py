"""
Миграция 062: персональные закрепления заявок (order_pins).
"""
import logging

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 062_order_pins")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS order_pins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(order_id, user_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_order_pins_user_created
            ON order_pins(user_id, created_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_order_pins_order
            ON order_pins(order_id)
            """
        )
        conn.commit()
    logger.info("Миграция 062_order_pins успешно применена")


def down():
    logger.warning("Откат миграции 062_order_pins")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS order_pins")
        conn.commit()
    logger.info("Откат 062_order_pins завершен")
