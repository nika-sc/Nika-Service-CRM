"""
Миграция 054: добавление service_id и part_id в salary_accruals.

Хранит, за какую конкретно услугу или товар начислена зарплата,
чтобы в отчёте отображать точное описание: «Мастер получил за услугу X».
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)

OLD_INDEX = "ux_salary_accruals_business_key"
NEW_INDEX = "ux_salary_accruals_business_key"


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute("PRAGMA table_info({})".format(table))
    return any(row[1] == column for row in cursor.fetchall())


def _index_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=? LIMIT 1",
        (name,),
    )
    return cursor.fetchone() is not None


def up():
    logger.info("Применение миграции 054_salary_accruals_service_part")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if not _column_exists(cursor, "salary_accruals", "service_id"):
            cursor.execute(
                "ALTER TABLE salary_accruals ADD COLUMN service_id INTEGER REFERENCES services(id)"
            )
            logger.info("Добавлена колонка salary_accruals.service_id")

        if not _column_exists(cursor, "salary_accruals", "part_id"):
            cursor.execute(
                "ALTER TABLE salary_accruals ADD COLUMN part_id INTEGER REFERENCES parts(id)"
            )
            logger.info("Добавлена колонка salary_accruals.part_id")

        # Обновляем существующие записи: когда calculated_from='service', service_id=calculated_from_id
        cursor.execute(
            """
            UPDATE salary_accruals
            SET service_id = calculated_from_id
            WHERE calculated_from = 'service' AND calculated_from_id IS NOT NULL AND service_id IS NULL
            """
        )
        # Аналогично для part
        cursor.execute(
            """
            UPDATE salary_accruals
            SET part_id = calculated_from_id
            WHERE calculated_from = 'part' AND calculated_from_id IS NOT NULL AND part_id IS NULL
            """
        )

        # Пересоздаём уникальный индекс с учётом service_id, part_id
        if _index_exists(cursor, OLD_INDEX):
            cursor.execute(f"DROP INDEX IF EXISTS {OLD_INDEX}")
            logger.info(f"Удалён старый индекс {OLD_INDEX}")

        cursor.execute(
            f"""
            CREATE UNIQUE INDEX IF NOT EXISTS {NEW_INDEX}
            ON salary_accruals (
                order_id,
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
            """
        )
        logger.info(f"Создан индекс {NEW_INDEX} с service_id, part_id")

        conn.commit()

    logger.info("Миграция 054_salary_accruals_service_part успешно применена")


def down():
    logger.info("Откат миграции 054_salary_accruals_service_part")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if _index_exists(cursor, NEW_INDEX):
            cursor.execute(f"DROP INDEX IF EXISTS {NEW_INDEX}")

        # SQLite не поддерживает DROP COLUMN напрямую — откат только индекса
        conn.commit()
    logger.info("Миграция 054 откачена (колонки service_id, part_id оставлены)")
