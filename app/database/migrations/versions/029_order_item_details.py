"""
Миграция 029: Детальные поля позиций заявки (для расчёта зарплаты/гарантии/скидок).

Добавляет:
- general_settings.default_warranty_days
- order_services: base_price, cost_price, discount_type, discount_value, warranty_days, executor_id
- order_parts: base_price, discount_type, discount_value, warranty_days, executor_id

Примечание:
- Для товаров себестоимость уже хранится в order_parts.purchase_price (снимок). UI будет писать туда.
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def up():
    logger.info("Применение миграции 029_order_item_details")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # general_settings.default_warranty_days
        if _column_exists(cursor, "general_settings", "default_warranty_days") is False:
            cursor.execute("ALTER TABLE general_settings ADD COLUMN default_warranty_days INTEGER DEFAULT 30")
            logger.info("Добавлена колонка general_settings.default_warranty_days")

        # order_services additional fields
        for col, ddl in [
            ("base_price", "ALTER TABLE order_services ADD COLUMN base_price DECIMAL(10, 2)"),
            ("cost_price", "ALTER TABLE order_services ADD COLUMN cost_price DECIMAL(10, 2)"),
            ("discount_type", "ALTER TABLE order_services ADD COLUMN discount_type TEXT"),
            ("discount_value", "ALTER TABLE order_services ADD COLUMN discount_value REAL"),
            ("warranty_days", "ALTER TABLE order_services ADD COLUMN warranty_days INTEGER"),
            ("executor_id", "ALTER TABLE order_services ADD COLUMN executor_id INTEGER"),
        ]:
            if not _column_exists(cursor, "order_services", col):
                cursor.execute(ddl)
                logger.info(f"Добавлена колонка order_services.{col}")

        # order_parts additional fields (purchase_price already exists)
        for col, ddl in [
            ("base_price", "ALTER TABLE order_parts ADD COLUMN base_price DECIMAL(10, 2)"),
            ("discount_type", "ALTER TABLE order_parts ADD COLUMN discount_type TEXT"),
            ("discount_value", "ALTER TABLE order_parts ADD COLUMN discount_value REAL"),
            ("warranty_days", "ALTER TABLE order_parts ADD COLUMN warranty_days INTEGER"),
            ("executor_id", "ALTER TABLE order_parts ADD COLUMN executor_id INTEGER"),
        ]:
            if not _column_exists(cursor, "order_parts", col):
                cursor.execute(ddl)
                logger.info(f"Добавлена колонка order_parts.{col}")

        conn.commit()
        logger.info("Миграция 029_order_item_details успешно применена")


def down():
    # SQLite не поддерживает DROP COLUMN без пересоздания таблиц.
    logger.warning("Откат миграции 029_order_item_details не поддержан (SQLite DROP COLUMN).")


