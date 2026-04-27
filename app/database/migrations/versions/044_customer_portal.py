"""
Миграция 044: Личный кабинет клиента.

Создает:
1. Таблицу customer_tokens для токенов доступа
2. Поля portal_enabled и portal_password_hash в customers
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
    logger.info("Применение миграции 044_customer_portal")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Добавляем поля в customers
        if not _column_exists(cursor, 'customers', 'portal_enabled'):
            logger.info("Добавление поля portal_enabled в таблицу customers...")
            cursor.execute('''
                ALTER TABLE customers
                ADD COLUMN portal_enabled INTEGER DEFAULT 0
            ''')
            logger.info("Поле portal_enabled добавлено")
        else:
            logger.info("Поле portal_enabled уже существует, пропускаем")
        
        if not _column_exists(cursor, 'customers', 'portal_password_hash'):
            logger.info("Добавление поля portal_password_hash в таблицу customers...")
            cursor.execute('''
                ALTER TABLE customers
                ADD COLUMN portal_password_hash TEXT
            ''')
            logger.info("Поле portal_password_hash добавлено")
        else:
            logger.info("Поле portal_password_hash уже существует, пропускаем")
        
        # 2. Создаем таблицу customer_tokens
        if not _table_exists(cursor, 'customer_tokens'):
            logger.info("Создание таблицы customer_tokens...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_customer_tokens_customer_id 
                ON customer_tokens(customer_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_customer_tokens_token 
                ON customer_tokens(token)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_customer_tokens_expires_at 
                ON customer_tokens(expires_at)
            ''')
            
            logger.info("Таблица customer_tokens создана")
        else:
            logger.info("Таблица customer_tokens уже существует, пропускаем")
        
        conn.commit()
        logger.info("Миграция 044_customer_portal успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 044_customer_portal")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицу customer_tokens
        if _table_exists(cursor, 'customer_tokens'):
            logger.info("Удаление таблицы customer_tokens...")
            cursor.execute('DROP TABLE IF EXISTS customer_tokens')
            logger.info("Таблица customer_tokens удалена")
        
        # SQLite не поддерживает DROP COLUMN напрямую
        if _column_exists(cursor, 'customers', 'portal_enabled'):
            logger.warning(
                "SQLite не поддерживает DROP COLUMN. "
                "Для удаления portal_enabled и portal_password_hash нужно пересоздать таблицу customers. "
                "Это не выполняется автоматически для безопасности."
            )
        
        conn.commit()
        logger.info("Миграция 044_customer_portal откачена")
