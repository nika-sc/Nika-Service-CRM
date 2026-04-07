"""
Миграция 059: реакции на сообщения staff chat.

Создает:
1. Таблицу staff_chat_reactions.
2. Индексы для быстрого чтения реакций.
3. Уникальность реакции по связке сообщение+пользователь+устройство+эмодзи.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 059_staff_chat_reactions")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_chat_reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                user_id INTEGER,
                username TEXT NOT NULL,
                actor_display_name TEXT NOT NULL DEFAULT '',
                client_instance_id TEXT NOT NULL DEFAULT '',
                emoji TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES staff_chat_messages(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_staff_chat_reactions_message
            ON staff_chat_reactions(message_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_staff_chat_reactions_message_emoji
            ON staff_chat_reactions(message_id, emoji)
            """
        )
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_staff_chat_reactions_actor
            ON staff_chat_reactions(message_id, user_id, actor_display_name, client_instance_id, emoji)
            """
        )

        conn.commit()
    logger.info("Миграция 059_staff_chat_reactions успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 059_staff_chat_reactions")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS staff_chat_reactions")
        conn.commit()
    logger.info("Откат 059_staff_chat_reactions завершен")
