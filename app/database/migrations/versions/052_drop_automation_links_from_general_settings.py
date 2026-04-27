"""
Миграция 052: удаление устаревших ссылочных полей из general_settings.

Удаляет колонки:
- portal_public_url
- review_url
- director_contact_url

SQLite не поддерживает надежный DROP COLUMN во всех окружениях, поэтому
используется пересоздание таблицы с переносом данных.
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


OBSOLETE_COLUMNS = {"portal_public_url", "review_url", "director_contact_url"}
TMP_TABLE = "general_settings_old_052"

TARGET_COLUMNS = [
    "id",
    "org_name",
    "phone",
    "address",
    "inn",
    "ogrn",
    "logo_url",
    "currency",
    "country",
    "updated_at",
    "default_warranty_days",
    "timezone_offset",
    "mail_server",
    "mail_port",
    "mail_use_tls",
    "mail_use_ssl",
    "mail_username",
    "mail_password",
    "mail_default_sender",
    "mail_timeout",
    "close_print_mode",
    "auto_email_order_accepted",
    "auto_email_status_update",
    "auto_email_order_ready",
    "auto_email_order_closed",
    "sms_enabled",
    "telegram_enabled",
    "signature_name",
    "signature_position",
    "director_email",
    "auto_email_director_order_accepted",
    "auto_email_director_order_closed",
]


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table,),
    )
    return cursor.fetchone() is not None


def _get_columns(cursor, table: str):
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def _quoted(columns):
    return ", ".join([f'"{c}"' for c in columns])


def up():
    logger.info("Применение миграции 052_drop_automation_links_from_general_settings")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if not _table_exists(cursor, "general_settings"):
            logger.warning("Таблица general_settings отсутствует. Пропуск миграции 052.")
            return

        existing_cols = _get_columns(cursor, "general_settings")
        to_drop = [c for c in existing_cols if c in OBSOLETE_COLUMNS]
        if not to_drop:
            logger.info("Устаревшие колонки уже отсутствуют. Миграция 052 пропущена.")
            return

        logger.info(f"Удаляем колонки general_settings: {', '.join(sorted(to_drop))}")

        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute(f"ALTER TABLE general_settings RENAME TO {TMP_TABLE}")

        cursor.execute(
            """
            CREATE TABLE general_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                org_name TEXT,
                phone TEXT,
                address TEXT,
                inn TEXT,
                ogrn TEXT,
                logo_url TEXT,
                currency TEXT DEFAULT 'RUB',
                country TEXT DEFAULT 'Россия',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                default_warranty_days INTEGER DEFAULT 30,
                timezone_offset INTEGER DEFAULT 3,
                mail_server TEXT,
                mail_port INTEGER DEFAULT 587,
                mail_use_tls INTEGER DEFAULT 1,
                mail_use_ssl INTEGER DEFAULT 0,
                mail_username TEXT,
                mail_password TEXT,
                mail_default_sender TEXT,
                mail_timeout INTEGER DEFAULT 3,
                close_print_mode TEXT DEFAULT 'choice',
                auto_email_order_accepted INTEGER DEFAULT 1,
                auto_email_status_update INTEGER DEFAULT 1,
                auto_email_order_ready INTEGER DEFAULT 1,
                auto_email_order_closed INTEGER DEFAULT 1,
                sms_enabled INTEGER DEFAULT 0,
                telegram_enabled INTEGER DEFAULT 0,
                signature_name TEXT,
                signature_position TEXT,
                director_email TEXT,
                auto_email_director_order_accepted INTEGER DEFAULT 1,
                auto_email_director_order_closed INTEGER DEFAULT 1
            )
            """
        )

        old_cols = _get_columns(cursor, TMP_TABLE)
        copy_cols = [c for c in TARGET_COLUMNS if c in old_cols]

        if copy_cols:
            cursor.execute(
                f"""
                INSERT INTO general_settings ({_quoted(copy_cols)})
                SELECT {_quoted(copy_cols)}
                FROM {TMP_TABLE}
                """
            )

        cursor.execute(f"DROP TABLE {TMP_TABLE}")
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()

    logger.info("Миграция 052_drop_automation_links_from_general_settings успешно применена")


def down():
    logger.info("Откат миграции 052_drop_automation_links_from_general_settings")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cols = _get_columns(cursor, "general_settings")

        if "portal_public_url" not in cols:
            cursor.execute("ALTER TABLE general_settings ADD COLUMN portal_public_url TEXT")
        if "review_url" not in cols:
            cursor.execute("ALTER TABLE general_settings ADD COLUMN review_url TEXT")
        if "director_contact_url" not in cols:
            cursor.execute("ALTER TABLE general_settings ADD COLUMN director_contact_url TEXT")

        conn.commit()

    logger.info("Откат миграции 052 выполнен: колонки ссылок восстановлены")
