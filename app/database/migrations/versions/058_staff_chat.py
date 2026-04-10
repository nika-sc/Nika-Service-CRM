"""
Миграция 058: внутренний чат сотрудников.

Создает:
1. Таблицу staff_chat_messages для хранения сообщений.
2. Таблицу staff_chat_attachments для хранения вложений.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 058_staff_chat")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_key TEXT NOT NULL DEFAULT 'global',
                user_id INTEGER,
                username TEXT NOT NULL,
                actor_display_name TEXT,
                client_instance_id TEXT,
                message_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                edited_at TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_chat_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
                file_path TEXT NOT NULL,
                is_image INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES staff_chat_messages(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_staff_chat_messages_room_created
            ON staff_chat_messages(room_key, created_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_staff_chat_messages_user_created
            ON staff_chat_messages(user_id, created_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_staff_chat_attachments_message
            ON staff_chat_attachments(message_id)
            """
        )

        conn.commit()
    logger.info("Миграция 058_staff_chat успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 058_staff_chat")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS staff_chat_attachments")
        cursor.execute("DROP TABLE IF EXISTS staff_chat_messages")
        conn.commit()
    logger.info("Откат 058_staff_chat завершен")
