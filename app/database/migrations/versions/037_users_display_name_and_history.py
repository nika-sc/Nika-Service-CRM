"""
Миграция 037: Добавление display_name в users и таблицы истории изменений прав/ролей.

Добавляет:
1. Поле display_name в таблицу users (ФИО для отображения, отдельно от username)
2. Таблицу user_role_history для истории изменений прав и ролей
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Проверяет существование колонки в таблице."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def _table_exists(cursor, table_name: str) -> bool:
    """Проверяет существование таблицы."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 037_users_display_name_and_history")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Добавляем поле display_name в таблицу users
        if not _column_exists(cursor, 'users', 'display_name'):
            logger.info("Добавление поля display_name в таблицу users...")
            cursor.execute('''
                ALTER TABLE users
                ADD COLUMN display_name TEXT
            ''')
            logger.info("Поле display_name добавлено")
        else:
            logger.info("Поле display_name уже существует, пропускаем")
        
        # 2. Заполняем display_name для существующих пользователей
        # Для админов используем username, для мастеров/менеджеров - из связанных таблиц
        logger.info("Заполнение display_name для существующих пользователей...")
        
        # Для админов: используем username
        cursor.execute('''
            UPDATE users
            SET display_name = username
            WHERE display_name IS NULL AND role = 'admin'
        ''')
        
        # Для мастеров: берем из таблицы masters
        cursor.execute('''
            UPDATE users
            SET display_name = (
                SELECT m.name
                FROM masters m
                WHERE m.user_id = users.id
                LIMIT 1
            )
            WHERE display_name IS NULL 
            AND (role LIKE 'master_%' OR role = 'master')
            AND EXISTS (SELECT 1 FROM masters m WHERE m.user_id = users.id)
        ''')
        
        # Для менеджеров: берем из таблицы managers
        cursor.execute('''
            UPDATE users
            SET display_name = (
                SELECT m.name
                FROM managers m
                WHERE m.user_id = users.id
                LIMIT 1
            )
            WHERE display_name IS NULL 
            AND (role LIKE 'manager_%' OR role = 'manager')
            AND EXISTS (SELECT 1 FROM managers m WHERE m.user_id = users.id)
        ''')
        
        # Для остальных: используем username
        cursor.execute('''
            UPDATE users
            SET display_name = username
            WHERE display_name IS NULL
        ''')
        
        logger.info("display_name заполнен для всех пользователей")
        
        # 3. Создаем таблицу истории изменений прав/ролей
        if not _table_exists(cursor, 'user_role_history'):
            logger.info("Создание таблицы user_role_history...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_role_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    changed_by INTEGER,
                    changed_by_username TEXT,
                    old_role TEXT,
                    new_role TEXT,
                    old_permission_ids TEXT,
                    new_permission_ids TEXT,
                    change_type TEXT NOT NULL CHECK(change_type IN ('role', 'permissions', 'both')),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
                )
            ''')
            
            # Индексы для быстрого поиска
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_role_history_user_id 
                ON user_role_history(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_role_history_created_at 
                ON user_role_history(created_at)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_role_history_changed_by 
                ON user_role_history(changed_by)
            ''')
            
            logger.info("Таблица user_role_history создана")
        else:
            logger.info("Таблица user_role_history уже существует, пропускаем")
        
        conn.commit()
        logger.info("Миграция 037_users_display_name_and_history успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 037_users_display_name_and_history")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицу истории (если существует)
        if _table_exists(cursor, 'user_role_history'):
            logger.info("Удаление таблицы user_role_history...")
            cursor.execute('DROP TABLE IF EXISTS user_role_history')
            logger.info("Таблица user_role_history удалена")
        
        # SQLite не поддерживает DROP COLUMN напрямую
        # Для удаления display_name нужно пересоздать таблицу
        # Но это может быть опасно, поэтому просто предупреждаем
        if _column_exists(cursor, 'users', 'display_name'):
            logger.warning(
                "SQLite не поддерживает DROP COLUMN. "
                "Для удаления display_name нужно пересоздать таблицу users. "
                "Это не выполняется автоматически для безопасности."
            )
        
        conn.commit()
        logger.info("Миграция 037_users_display_name_and_history откачена")
