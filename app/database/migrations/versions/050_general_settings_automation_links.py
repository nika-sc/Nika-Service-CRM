"""
Миграция 050: Расширение general_settings для коммуникаций/автоматизаций.

Добавляет:
- portal_public_url, review_url, director_contact_url
- close_print_mode
- auto_email_* флаги
- sms_enabled, telegram_enabled
- signature_name, signature_position
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def up():
    logger.info("Применение миграции 050_general_settings_automation_links")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        t = "general_settings"

        additions = [
            ("portal_public_url", "TEXT"),
            ("review_url", "TEXT"),
            ("director_contact_url", "TEXT"),
            ("close_print_mode", "TEXT DEFAULT 'choice'"),
            ("auto_email_order_accepted", "INTEGER DEFAULT 1"),
            ("auto_email_status_update", "INTEGER DEFAULT 1"),
            ("auto_email_order_ready", "INTEGER DEFAULT 1"),
            ("auto_email_order_closed", "INTEGER DEFAULT 1"),
            ("sms_enabled", "INTEGER DEFAULT 0"),
            ("telegram_enabled", "INTEGER DEFAULT 0"),
            ("signature_name", "TEXT"),
            ("signature_position", "TEXT"),
        ]

        for col_name, col_def in additions:
            if not _column_exists(cursor, t, col_name):
                cursor.execute(f"ALTER TABLE {t} ADD COLUMN {col_name} {col_def}")
                logger.info(f"Добавлена колонка general_settings.{col_name}")

        conn.commit()
    logger.info("Миграция 050_general_settings_automation_links успешно применена")


def down():
    logger.warning("Откат миграции 050 не поддержан (SQLite DROP COLUMN).")
