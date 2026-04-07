"""
Миграция 023: Защита от дублей кассовых операций по оплатам.

Добавляет UNIQUE индекс на cash_transactions.payment_id (только когда payment_id не NULL),
чтобы одна оплата (payments.id) не могла создать несколько записей в cash_transactions.

Важно:
- Это не запрещает несколько оплат по одной заявке — только дубль по одному и тому же payment_id.
"""

from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up() -> None:
    """Применяет миграцию."""
    logger.info("Применение миграции 023_cash_transactions_payment_unique: UNIQUE по payment_id в cash_transactions")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1) Проверяем дубликаты payment_id (на всякий случай)
        try:
            cursor.execute("""
                SELECT payment_id, COUNT(*) AS cnt
                FROM cash_transactions
                WHERE payment_id IS NOT NULL
                GROUP BY payment_id
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            if duplicates:
                logger.warning(
                    f"Найдено {len(duplicates)} payment_id с дублями в cash_transactions. "
                    "UNIQUE индекс не будет создан, пока дубли не будут устранены."
                )
                # Не пытаемся автоматически удалять — это риск потери финансовой истории.
                conn.commit()
                return
        except sqlite3.OperationalError as e:
            logger.error(f"Не удалось проверить дубли payment_id: {e}")

        # 2) Создаем partial UNIQUE index (SQLite поддерживает WHERE в CREATE INDEX)
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS ux_cash_transactions_payment_id
                ON cash_transactions(payment_id)
                WHERE payment_id IS NOT NULL
            """)
            conn.commit()
            logger.info("UNIQUE индекс ux_cash_transactions_payment_id создан")
        except sqlite3.OperationalError as e:
            logger.error(f"Не удалось создать UNIQUE индекс ux_cash_transactions_payment_id: {e}")
            conn.commit()


def down() -> None:
    """Откат миграции."""
    logger.info("Откат миграции 023_cash_transactions_payment_unique")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DROP INDEX IF EXISTS ux_cash_transactions_payment_id")
            conn.commit()
        except sqlite3.OperationalError as e:
            logger.error(f"Не удалось удалить индекс ux_cash_transactions_payment_id: {e}")
            conn.commit()


