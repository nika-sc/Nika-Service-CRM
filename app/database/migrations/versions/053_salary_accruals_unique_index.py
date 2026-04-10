"""
Миграция 053: защита от дублей в salary_accruals.

Добавляет уникальный индекс на ключ начисления, чтобы одинаковые начисления
по одной заявке/сотруднику/источнику не могли записаться повторно.
Перед созданием индекса удаляет уже существующие дубли (оставляет запись с минимальным id).
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)

INDEX_NAME = "ux_salary_accruals_business_key"


def _index_exists(cursor, index_name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=? LIMIT 1",
        (index_name,),
    )
    return cursor.fetchone() is not None


def up():
    logger.info("Применение миграции 053_salary_accruals_unique_index")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1) Чистим исторические дубли, чтобы уникальный индекс создавался без ошибок.
        cursor.execute(
            """
            DELETE FROM salary_accruals
            WHERE id IN (
                SELECT sa.id
                FROM salary_accruals sa
                INNER JOIN (
                    SELECT
                        MIN(id) AS keep_id,
                        order_id,
                        user_id,
                        role,
                        rule_type,
                        rule_value,
                        calculated_from,
                        COALESCE(calculated_from_id, -1) AS calc_from_id_norm,
                        amount_cents,
                        base_amount_cents,
                        profit_cents,
                        COALESCE(vat_included, 0) AS vat_included_norm,
                        COUNT(*) AS cnt
                    FROM salary_accruals
                    GROUP BY
                        order_id,
                        user_id,
                        role,
                        rule_type,
                        rule_value,
                        calculated_from,
                        COALESCE(calculated_from_id, -1),
                        amount_cents,
                        base_amount_cents,
                        profit_cents,
                        COALESCE(vat_included, 0)
                    HAVING COUNT(*) > 1
                ) d
                    ON sa.order_id = d.order_id
                   AND sa.user_id = d.user_id
                   AND sa.role = d.role
                   AND sa.rule_type = d.rule_type
                   AND sa.rule_value = d.rule_value
                   AND sa.calculated_from = d.calculated_from
                   AND COALESCE(sa.calculated_from_id, -1) = d.calc_from_id_norm
                   AND sa.amount_cents = d.amount_cents
                   AND sa.base_amount_cents = d.base_amount_cents
                   AND sa.profit_cents = d.profit_cents
                   AND COALESCE(sa.vat_included, 0) = d.vat_included_norm
                WHERE sa.id <> d.keep_id
            )
            """
        )
        deleted = cursor.rowcount if cursor.rowcount is not None else 0
        if deleted:
            logger.info(f"Удалено дублирующих salary_accruals: {deleted}")

        # 2) Уникальный индекс по бизнес-ключу начисления.
        if not _index_exists(cursor, INDEX_NAME):
            cursor.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
                ON salary_accruals (
                    order_id,
                    user_id,
                    role,
                    rule_type,
                    rule_value,
                    calculated_from,
                    IFNULL(calculated_from_id, -1),
                    amount_cents,
                    base_amount_cents,
                    profit_cents,
                    IFNULL(vat_included, 0)
                )
                """
            )
            logger.info(f"Создан индекс {INDEX_NAME}")
        else:
            logger.info(f"Индекс {INDEX_NAME} уже существует")

        conn.commit()

    logger.info("Миграция 053_salary_accruals_unique_index успешно применена")


def down():
    logger.info("Откат миграции 053_salary_accruals_unique_index")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
        conn.commit()
    logger.info(f"Индекс {INDEX_NAME} удален")
