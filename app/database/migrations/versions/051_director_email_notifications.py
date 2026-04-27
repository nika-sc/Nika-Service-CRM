"""
Миграция 051: Настройки email-уведомлений директору.

Добавляет в general_settings:
- director_email
- auto_email_director_order_accepted
- auto_email_director_order_closed
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def up():
    logger.info("Применение миграции 051_director_email_notifications")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        table = "general_settings"

        additions = [
            ("director_email", "TEXT"),
            ("auto_email_director_order_accepted", "INTEGER DEFAULT 1"),
            ("auto_email_director_order_closed", "INTEGER DEFAULT 1"),
        ]

        for col_name, col_def in additions:
            if not _column_exists(cursor, table, col_name):
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                logger.info(f"Добавлена колонка general_settings.{col_name}")

        conn.commit()
    logger.info("Миграция 051_director_email_notifications успешно применена")


def down():
    logger.warning("Откат миграции 051 не поддержан (SQLite DROP COLUMN).")

