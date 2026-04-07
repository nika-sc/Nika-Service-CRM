"""
Миграция 038: Система уведомлений.

Создает:
1. Таблицу notifications для хранения уведомлений
2. Таблицу notification_preferences для настроек уведомлений пользователей
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _table_exists(cursor, table_name: str) -> bool:
    """Проверяет существование таблицы."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 038_notifications_system")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Создаем таблицу notifications
        if not _table_exists(cursor, 'notifications'):
            logger.info("Создание таблицы notifications...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('email', 'push', 'in_app')),
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id INTEGER,
                    read_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы для быстрого поиска
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notifications_user_id 
                ON notifications(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notifications_created_at 
                ON notifications(created_at DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notifications_read_at 
                ON notifications(read_at)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notifications_entity 
                ON notifications(entity_type, entity_id)
            ''')
            
            logger.info("Таблица notifications создана")
        else:
            logger.info("Таблица notifications уже существует, пропускаем")
        
        # 2. Создаем таблицу notification_preferences
        if not _table_exists(cursor, 'notification_preferences'):
            logger.info("Создание таблицы notification_preferences...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    notification_type TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    email_enabled INTEGER DEFAULT 1,
                    push_enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, notification_type)
                )
            ''')
            
            # Индексы
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notification_preferences_user_id 
                ON notification_preferences(user_id)
            ''')
            
            logger.info("Таблица notification_preferences создана")
        else:
            logger.info("Таблица notification_preferences уже существует, пропускаем")
        
        conn.commit()
        logger.info("Миграция 038_notifications_system успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 038_notifications_system")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицы в обратном порядке
        if _table_exists(cursor, 'notification_preferences'):
            logger.info("Удаление таблицы notification_preferences...")
            cursor.execute('DROP TABLE IF EXISTS notification_preferences')
            logger.info("Таблица notification_preferences удалена")
        
        if _table_exists(cursor, 'notifications'):
            logger.info("Удаление таблицы notifications...")
            cursor.execute('DROP TABLE IF EXISTS notifications')
            logger.info("Таблица notifications удалена")
        
        conn.commit()
        logger.info("Миграция 038_notifications_system откачена")
