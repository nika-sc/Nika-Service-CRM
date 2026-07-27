"""
Миграция 063: события демо-статистики посещений (demo_visitor_events).
"""
import logging

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 063_demo_visitor_events")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS demo_visitor_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NULL,
                username TEXT NULL,
                ip TEXT NULL,
                user_agent TEXT NULL,
                path TEXT NULL,
                event_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_created
            ON demo_visitor_events(created_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_user_created
            ON demo_visitor_events(user_id, created_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_demo_visitor_events_type_created
            ON demo_visitor_events(event_type, created_at DESC)
            """
        )
        conn.commit()
    logger.info("Миграция 063_demo_visitor_events успешно применена")


def down():
    logger.warning("Откат миграции 063_demo_visitor_events")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS demo_visitor_events")
        conn.commit()
    logger.info("Откат 063_demo_visitor_events завершен")
