"""
Миграция 039: Расширение системы комментариев.

Добавляет:
1. Поле user_id в order_comments (FK к users)
2. Поле mentions в order_comments (JSON массив user_id)
3. Таблицу comment_attachments для хранения файлов
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
    logger.info("Применение миграции 039_extend_comments_system")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Добавляем поле user_id в order_comments
        if not _column_exists(cursor, 'order_comments', 'user_id'):
            logger.info("Добавление поля user_id в таблицу order_comments...")
            cursor.execute('''
                ALTER TABLE order_comments
                ADD COLUMN user_id INTEGER
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_order_comments_user_id 
                ON order_comments(user_id)
            ''')
            logger.info("Поле user_id добавлено")
        else:
            logger.info("Поле user_id уже существует, пропускаем")
        
        # 2. Добавляем поле mentions в order_comments
        if not _column_exists(cursor, 'order_comments', 'mentions'):
            logger.info("Добавление поля mentions в таблицу order_comments...")
            cursor.execute('''
                ALTER TABLE order_comments
                ADD COLUMN mentions TEXT
            ''')
            logger.info("Поле mentions добавлено")
        else:
            logger.info("Поле mentions уже существует, пропускаем")
        
        # 3. Создаем таблицу comment_attachments
        if not _table_exists(cursor, 'comment_attachments'):
            logger.info("Создание таблицы comment_attachments...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS comment_attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    mime_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (comment_id) REFERENCES order_comments(id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_comment_attachments_comment_id 
                ON comment_attachments(comment_id)
            ''')
            
            logger.info("Таблица comment_attachments создана")
        else:
            logger.info("Таблица comment_attachments уже существует, пропускаем")
        
        conn.commit()
        logger.info("Миграция 039_extend_comments_system успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 039_extend_comments_system")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицу comment_attachments
        if _table_exists(cursor, 'comment_attachments'):
            logger.info("Удаление таблицы comment_attachments...")
            cursor.execute('DROP TABLE IF EXISTS comment_attachments')
            logger.info("Таблица comment_attachments удалена")
        
        # SQLite не поддерживает DROP COLUMN напрямую
        # Для удаления полей нужно пересоздать таблицу
        # Но это может быть опасно, поэтому просто предупреждаем
        if _column_exists(cursor, 'order_comments', 'user_id'):
            logger.warning(
                "SQLite не поддерживает DROP COLUMN. "
                "Для удаления user_id и mentions нужно пересоздать таблицу order_comments. "
                "Это не выполняется автоматически для безопасности."
            )
        
        conn.commit()
        logger.info("Миграция 039_extend_comments_system откачена")
