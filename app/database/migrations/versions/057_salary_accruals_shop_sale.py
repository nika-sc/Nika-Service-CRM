"""
Миграция 057: поддержка начислений зарплаты по продажам магазина.

- Добавляет shop_sale_id в salary_accruals.
- Делает order_id допускающим NULL (для начислений по магазину только shop_sale_id задан).
- Ограничение: ровно один из order_id или shop_sale_id должен быть задан.
- Пересоздаёт уникальный индекс с учётом shop_sale_id.
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)

INDEX_NAME = "ux_salary_accruals_business_key"


def _index_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=? LIMIT 1",
        (name,),
    )
    return cursor.fetchone() is not None


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    )
    return cursor.fetchone() is not None


def up():
    logger.info("Применение миграции 057_salary_accruals_shop_sale")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if not _table_exists(cursor, "salary_accruals"):
            logger.info("Таблица salary_accruals отсутствует, миграция 057 пропущена")
            return

        # Пересоздаём таблицу: order_id nullable, добавляем shop_sale_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS salary_accruals_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                shop_sale_id INTEGER REFERENCES shop_sales(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                base_amount_cents INTEGER NOT NULL,
                profit_cents INTEGER NOT NULL,
                rule_type TEXT NOT NULL,
                rule_value REAL NOT NULL,
                calculated_from TEXT NOT NULL,
                calculated_from_id INTEGER,
                service_id INTEGER REFERENCES services(id),
                part_id INTEGER REFERENCES parts(id),
                vat_included INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (
                    (order_id IS NOT NULL AND shop_sale_id IS NULL)
                    OR (order_id IS NULL AND shop_sale_id IS NOT NULL)
                )
            )
        """)

        cursor.execute("""
            INSERT INTO salary_accruals_new (
                id, order_id, shop_sale_id, user_id, role,
                amount_cents, base_amount_cents, profit_cents,
                rule_type, rule_value, calculated_from, calculated_from_id,
                service_id, part_id, vat_included, created_at
            )
            SELECT
                id, order_id, NULL, user_id, role,
                amount_cents, base_amount_cents, profit_cents,
                rule_type, rule_value, calculated_from, calculated_from_id,
                service_id, part_id, vat_included, created_at
            FROM salary_accruals
        """)

        cursor.execute("DROP TABLE salary_accruals")
        cursor.execute("ALTER TABLE salary_accruals_new RENAME TO salary_accruals")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_salary_accruals_order_id ON salary_accruals(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_salary_accruals_shop_sale_id ON salary_accruals(shop_sale_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_salary_accruals_user_id ON salary_accruals(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_salary_accruals_role ON salary_accruals(role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_salary_accruals_created_at ON salary_accruals(created_at)")

        if _index_exists(cursor, INDEX_NAME):
            cursor.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")

        cursor.execute(f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
            ON salary_accruals (
                COALESCE(order_id, -1),
                COALESCE(shop_sale_id, -1),
                user_id,
                role,
                rule_type,
                rule_value,
                calculated_from,
                IFNULL(calculated_from_id, -1),
                IFNULL(service_id, -1),
                IFNULL(part_id, -1),
                amount_cents,
                base_amount_cents,
                profit_cents,
                IFNULL(vat_included, 0)
            )
        """)

        conn.commit()
    logger.info("Миграция 057_salary_accruals_shop_sale успешно применена")


def down():
    logger.info("Откат миграции 057_salary_accruals_shop_sale")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if _index_exists(cursor, INDEX_NAME):
            cursor.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
        cursor.execute("DROP INDEX IF EXISTS idx_salary_accruals_shop_sale_id")
        # Восстановить старую таблицу с order_id NOT NULL можно только пересозданием и копированием
        # без строк с shop_sale_id IS NOT NULL (или удалить их). Для краткости откат только снимает индекс.
        conn.commit()
    logger.info("Откат 057 завершён (колонка shop_sale_id и nullable order_id сохранены)")
