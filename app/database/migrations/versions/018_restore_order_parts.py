"""
Миграция 018: Восстановление таблицы order_parts.

Зачем:
- В UI заявки (`order_detail.html`) есть модуль "Запчасти" и "Объединенная продажа"
  (услуги + запчасти + оплата), который ожидает API:
  - POST /api/orders/<order_id>/parts
  - DELETE /api/order-parts/<order_part_id>
- Ранее таблица `order_parts` была удалена миграцией 006, из-за чего запчасти
  не могут участвовать в заявке/отчетах/марже.

Примечание:
- Храним цену продажи (`price`) и снимок себестоимости (`purchase_price`) на момент продажи,
  чтобы отчеты не "плыли" при изменении цен в справочнике.
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 018_restore_order_parts: восстановление таблицы order_parts")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Создаем таблицу, если отсутствует
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_parts'")
        if cursor.fetchone():
            logger.info("Таблица order_parts уже существует, пропускаем создание")
            return

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS order_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                purchase_price DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES parts(id)
            )
            """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_parts_order_id ON order_parts(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_parts_part_id ON order_parts(part_id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_order_parts_order_part ON order_parts(order_id, part_id)")

        conn.commit()
        logger.info("Миграция 018_restore_order_parts успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 018_restore_order_parts: удаление таблицы order_parts")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP INDEX IF EXISTS ux_order_parts_order_part")
        cursor.execute("DROP INDEX IF EXISTS idx_order_parts_order_id")
        cursor.execute("DROP INDEX IF EXISTS idx_order_parts_part_id")
        cursor.execute("DROP TABLE IF EXISTS order_parts")
        conn.commit()


