"""
Миграция 049: Настройки почты (SMTP) в общих настройках.

Добавляет в general_settings:
- mail_server, mail_port, mail_use_tls, mail_use_ssl
- mail_username, mail_password, mail_default_sender, mail_timeout
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def up():
    logger.info("Применение миграции 049_general_settings_mail")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        t = "general_settings"

        if not _column_exists(cursor, t, "mail_server"):
            cursor.execute("ALTER TABLE general_settings ADD COLUMN mail_server TEXT")
            logger.info("Добавлена колонка general_settings.mail_server")
        if not _column_exists(cursor, t, "mail_port"):
            cursor.execute("ALTER TABLE general_settings ADD COLUMN mail_port INTEGER DEFAULT 587")
            logger.info("Добавлена колонка general_settings.mail_port")
        if not _column_exists(cursor, t, "mail_use_tls"):
            cursor.execute("ALTER TABLE general_settings ADD COLUMN mail_use_tls INTEGER DEFAULT 1")
            logger.info("Добавлена колонка general_settings.mail_use_tls")
        if not _column_exists(cursor, t, "mail_use_ssl"):
            cursor.execute("ALTER TABLE general_settings ADD COLUMN mail_use_ssl INTEGER DEFAULT 0")
            logger.info("Добавлена колонка general_settings.mail_use_ssl")
        if not _column_exists(cursor, t, "mail_username"):
            cursor.execute("ALTER TABLE general_settings ADD COLUMN mail_username TEXT")
            logger.info("Добавлена колонка general_settings.mail_username")
        if not _column_exists(cursor, t, "mail_password"):
            cursor.execute("ALTER TABLE general_settings ADD COLUMN mail_password TEXT")
            logger.info("Добавлена колонка general_settings.mail_password")
        if not _column_exists(cursor, t, "mail_default_sender"):
            cursor.execute("ALTER TABLE general_settings ADD COLUMN mail_default_sender TEXT")
            logger.info("Добавлена колонка general_settings.mail_default_sender")
        if not _column_exists(cursor, t, "mail_timeout"):
            cursor.execute("ALTER TABLE general_settings ADD COLUMN mail_timeout INTEGER DEFAULT 3")
            logger.info("Добавлена колонка general_settings.mail_timeout")

        conn.commit()
    logger.info("Миграция 049_general_settings_mail успешно применена")


def down():
    logger.warning("Откат миграции 049: SQLite не поддерживает DROP COLUMN.")
