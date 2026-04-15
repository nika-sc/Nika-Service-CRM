"""
Миграция 060: курсоры прочитанного в staff chat + основа для поиска/лимитов (таблица).

Создает таблицу staff_chat_read_cursors: последнее прочитанное сообщение
на связке комната + пользователь + подпись с ПК + client_instance_id.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 060_staff_chat_read_cursors")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_chat_read_cursors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_key TEXT NOT NULL DEFAULT 'global',
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL DEFAULT '',
                actor_display_name TEXT NOT NULL DEFAULT '',
                client_instance_id TEXT NOT NULL DEFAULT '',
                last_read_message_id INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_staff_chat_read_cursors_actor
            ON staff_chat_read_cursors(room_key, user_id, actor_display_name, client_instance_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_staff_chat_read_cursors_room
            ON staff_chat_read_cursors(room_key)
            """
        )

        conn.commit()
    logger.info("Миграция 060_staff_chat_read_cursors успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 060_staff_chat_read_cursors")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS staff_chat_read_cursors")
        conn.commit()
    logger.info("Откат 060_staff_chat_read_cursors завершен")
