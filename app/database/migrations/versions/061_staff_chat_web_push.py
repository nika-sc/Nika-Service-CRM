"""
Миграция 061: подписки Web Push для чата сотрудников (VAPID + endpoint).
"""
import logging

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 061_staff_chat_web_push")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_chat_web_push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                user_agent TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, endpoint)
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_staff_chat_web_push_user
            ON staff_chat_web_push_subscriptions(user_id)
            """
        )
        conn.commit()
    logger.info("Миграция 061_staff_chat_web_push успешно применена")


def down():
    logger.warning("Откат миграции 061_staff_chat_web_push")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS staff_chat_web_push_subscriptions")
        conn.commit()
    logger.info("Откат 061_staff_chat_web_push завершен")
