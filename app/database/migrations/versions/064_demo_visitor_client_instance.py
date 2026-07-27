"""
Миграция 064: client_instance_id для демо-статистики (разные браузеры).
"""
import logging

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 064_demo_visitor_client_instance")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(demo_visitor_events)")
        cols = {row[1] for row in cursor.fetchall()}
        if "client_instance_id" not in cols:
            cursor.execute("ALTER TABLE demo_visitor_events ADD COLUMN client_instance_id TEXT NULL")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_client_created
            ON demo_visitor_events(client_instance_id, created_at DESC)
            """
        )
        conn.commit()
    logger.info("Миграция 064_demo_visitor_client_instance успешно применена")


def down():
    logger.warning("Откат 064: SQLite не удаляет колонку client_instance_id автоматически")
