"""
Миграция 017: Нормализация предоплаты (orders.prepayment_cents).

Добавляет:
- orders.prepayment_cents INTEGER NOT NULL DEFAULT 0 (сумма в копейках)
- индекс по prepayment_cents

Миграция данных:
- orders.prepayment (TEXT) -> prepayment_cents = round(prepayment * 100)

Старое поле prepayment (TEXT) сохраняем для обратной совместимости.
"""

import logging
import sqlite3
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 017_orders_prepayment_cents")
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cur = conn.cursor()

        cur.execute("PRAGMA table_info(orders)")
        cols = [r[1] for r in cur.fetchall()]
        if "prepayment_cents" not in cols:
            cur.execute("ALTER TABLE orders ADD COLUMN prepayment_cents INTEGER NOT NULL DEFAULT 0")
            logger.info("Добавлена колонка orders.prepayment_cents")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_prepayment_cents ON orders(prepayment_cents)")

        # Перенос значений из TEXT prepayment
        # SQLite: CAST('' AS REAL) -> 0.0, поэтому защищаемся TRIM != ''
        cur.execute("""
            UPDATE orders
            SET prepayment_cents = CAST(ROUND(CAST(prepayment AS REAL) * 100.0) AS INTEGER)
            WHERE (prepayment_cents IS NULL OR prepayment_cents = 0)
              AND prepayment IS NOT NULL AND TRIM(prepayment) != ''
        """)

        conn.commit()
        logger.info("Миграция 017_orders_prepayment_cents успешно применена")


def down():
    logger.warning("Откат миграции 017_orders_prepayment_cents не поддерживается (SQLite DROP COLUMN отсутствует)")


