"""
Миграция 034: Таблицы для премий, штрафов и выплат зарплаты.

Создает таблицы:
- salary_bonuses (премии)
- salary_fines (штрафы)
- salary_payments (выплаты зарплаты)
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _table_exists(cursor, table_name: str) -> bool:
    """Проверяет существование таблицы."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 034_salary_bonuses_fines_payments")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Таблица salary_bonuses (премии)
        if not _table_exists(cursor, "salary_bonuses"):
            logger.info("Создание таблицы salary_bonuses...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS salary_bonuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('master', 'manager')),
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    reason TEXT,
                    order_id INTEGER,
                    bonus_date DATE NOT NULL,
                    created_by_id INTEGER,
                    created_by_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_bonuses_user_id ON salary_bonuses(user_id, role)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_bonuses_date ON salary_bonuses(bonus_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_bonuses_order_id ON salary_bonuses(order_id)')
            logger.info("Таблица salary_bonuses создана")
        
        # 2. Таблица salary_fines (штрафы)
        if not _table_exists(cursor, "salary_fines"):
            logger.info("Создание таблицы salary_fines...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS salary_fines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('master', 'manager')),
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    reason TEXT NOT NULL,
                    order_id INTEGER,
                    fine_date DATE NOT NULL,
                    created_by_id INTEGER,
                    created_by_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_fines_user_id ON salary_fines(user_id, role)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_fines_date ON salary_fines(fine_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_fines_order_id ON salary_fines(order_id)')
            logger.info("Таблица salary_fines создана")
        
        # 3. Таблица salary_payments (выплаты зарплаты)
        if not _table_exists(cursor, "salary_payments"):
            logger.info("Создание таблицы salary_payments...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS salary_payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('master', 'manager')),
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    payment_date DATE NOT NULL,
                    period_start DATE,
                    period_end DATE,
                    payment_type TEXT DEFAULT 'salary' CHECK(payment_type IN ('salary', 'bonus', 'advance')),
                    comment TEXT,
                    created_by_id INTEGER,
                    created_by_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_payments_user_id ON salary_payments(user_id, role)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_payments_date ON salary_payments(payment_date)')
            logger.info("Таблица salary_payments создана")
        
        conn.commit()
        logger.info("Миграция 034_salary_bonuses_fines_payments успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 034_salary_bonuses_fines_payments")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        tables = ['salary_payments', 'salary_fines', 'salary_bonuses']
        
        for table in tables:
            try:
                if _table_exists(cursor, table):
                    cursor.execute(f'DROP TABLE IF EXISTS {table}')
                    logger.info(f"Таблица {table} удалена")
            except Exception as e:
                logger.warning(f"Не удалось удалить таблицу {table}: {e}")
        
        conn.commit()
        logger.info("Миграция 034_salary_bonuses_fines_payments откачена")
