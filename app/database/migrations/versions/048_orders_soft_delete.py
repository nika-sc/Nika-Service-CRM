"""
Миграция 048: Soft-delete для заявок.

Добавляет поля:
- is_deleted
- deleted_at
- deleted_by_id
- deleted_reason
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 048_orders_soft_delete")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(orders)")
        columns = {row[1] for row in cursor.fetchall()}

        if "is_deleted" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0")
            logger.info("Добавлена колонка orders.is_deleted")

        if "deleted_at" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN deleted_at TIMESTAMP")
            logger.info("Добавлена колонка orders.deleted_at")

        if "deleted_by_id" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN deleted_by_id INTEGER")
            logger.info("Добавлена колонка orders.deleted_by_id")

        if "deleted_reason" not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN deleted_reason TEXT")
            logger.info("Добавлена колонка orders.deleted_reason")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_is_deleted ON orders(is_deleted)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_hidden_deleted ON orders(hidden, is_deleted)")
        conn.commit()


def down():
    """
    Откат миграции.

    SQLite не поддерживает DROP COLUMN без пересоздания таблицы,
    поэтому откатываем только индексы.
    """
    logger.info("Откат миграции 048_orders_soft_delete")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP INDEX IF EXISTS idx_orders_is_deleted")
        cursor.execute("DROP INDEX IF EXISTS idx_orders_hidden_deleted")
        conn.commit()
