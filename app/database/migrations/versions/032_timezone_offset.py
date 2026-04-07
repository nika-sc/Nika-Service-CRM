"""
Миграция 032: Добавление настройки часового пояса.

Добавляет:
- general_settings.timezone_offset - смещение часового пояса от UTC в часах (по умолчанию 3 для Москвы)
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def up():
    logger.info("Применение миграции 032_timezone_offset")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # general_settings.timezone_offset
        if _column_exists(cursor, "general_settings", "timezone_offset") is False:
            cursor.execute("ALTER TABLE general_settings ADD COLUMN timezone_offset INTEGER DEFAULT 3")
            logger.info("Добавлена колонка general_settings.timezone_offset")
            
            # Устанавливаем значение по умолчанию 3 (Москва) для существующих записей
            cursor.execute("UPDATE general_settings SET timezone_offset = 3 WHERE timezone_offset IS NULL")
            logger.info("Установлено значение по умолчанию timezone_offset = 3 для существующих записей")

        conn.commit()
        logger.info("Миграция 032_timezone_offset успешно применена")


def down():
    # SQLite не поддерживает DROP COLUMN без пересоздания таблиц.
    logger.warning("Откат миграции 032_timezone_offset не поддержан (SQLite DROP COLUMN).")
