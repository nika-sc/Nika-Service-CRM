"""
Миграция 040: Система задач и дедлайнов.

Создает:
1. Таблицу tasks для задач
2. Таблицу task_checklists для чек-листов задач
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
    logger.info("Применение миграции 040_tasks_system")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Создаем таблицу tasks
        if not _table_exists(cursor, 'tasks'):
            logger.info("Создание таблицы tasks...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    assigned_to INTEGER,
                    created_by INTEGER NOT NULL,
                    deadline TIMESTAMP,
                    priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
                    status TEXT DEFAULT 'todo' CHECK(status IN ('todo', 'in_progress', 'done', 'cancelled')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_order_id 
                ON tasks(order_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to 
                ON tasks(assigned_to)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_status 
                ON tasks(status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_deadline 
                ON tasks(deadline)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_created_by 
                ON tasks(created_by)
            ''')
            
            logger.info("Таблица tasks создана")
        else:
            logger.info("Таблица tasks уже существует, пропускаем")
        
        # 2. Создаем таблицу task_checklists
        if not _table_exists(cursor, 'task_checklists'):
            logger.info("Создание таблицы task_checklists...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_checklists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    item_text TEXT NOT NULL,
                    is_completed INTEGER DEFAULT 0,
                    item_order INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            ''')
            
            # Индексы
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_task_checklists_task_id 
                ON task_checklists(task_id)
            ''')
            
            logger.info("Таблица task_checklists создана")
        else:
            logger.info("Таблица task_checklists уже существует, пропускаем")
        
        conn.commit()
        logger.info("Миграция 040_tasks_system успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 040_tasks_system")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем таблицы в обратном порядке
        if _table_exists(cursor, 'task_checklists'):
            logger.info("Удаление таблицы task_checklists...")
            cursor.execute('DROP TABLE IF EXISTS task_checklists')
            logger.info("Таблица task_checklists удалена")
        
        if _table_exists(cursor, 'tasks'):
            logger.info("Удаление таблицы tasks...")
            cursor.execute('DROP TABLE IF EXISTS tasks')
            logger.info("Таблица tasks удалена")
        
        conn.commit()
        logger.info("Миграция 040_tasks_system откачена")
