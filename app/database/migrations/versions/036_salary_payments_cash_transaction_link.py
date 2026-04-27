"""
Миграция 036: Добавление связи salary_payments с cash_transactions.

Добавляет поле cash_transaction_id в таблицу salary_payments для явной связи
с кассовыми операциями, созданными при выплате зарплаты.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    """Проверяет существование колонки в таблице."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 036_salary_payments_cash_transaction_link")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем существование таблицы salary_payments
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='salary_payments'")
        if not cursor.fetchone():
            logger.warning("Таблица salary_payments не существует. Пропускаем миграцию.")
            return
        
        # Добавляем поле cash_transaction_id, если его еще нет
        if not _column_exists(cursor, 'salary_payments', 'cash_transaction_id'):
            logger.info("Добавление поля cash_transaction_id в таблицу salary_payments...")
            cursor.execute('''
                ALTER TABLE salary_payments
                ADD COLUMN cash_transaction_id INTEGER
            ''')
            
            # Добавляем внешний ключ (SQLite не поддерживает ADD CONSTRAINT, но можем создать индекс)
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_salary_payments_cash_transaction_id 
                ON salary_payments(cash_transaction_id)
            ''')
            
            # Добавляем комментарий через PRAGMA (SQLite не поддерживает комментарии напрямую)
            # Но можем создать триггер для проверки целостности
            logger.info("Поле cash_transaction_id добавлено")
        else:
            logger.info("Поле cash_transaction_id уже существует, пропускаем")
        
        conn.commit()
        logger.info("Миграция 036_salary_payments_cash_transaction_link успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 036_salary_payments_cash_transaction_link")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # SQLite не поддерживает DROP COLUMN напрямую
        # Нужно пересоздать таблицу без этого поля
        if _column_exists(cursor, 'salary_payments', 'cash_transaction_id'):
            logger.info("Удаление поля cash_transaction_id из таблицы salary_payments...")
            
            # Создаем временную таблицу без cash_transaction_id
            cursor.execute('''
                CREATE TABLE salary_payments_new (
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
            
            # Копируем данные (без cash_transaction_id)
            cursor.execute('''
                INSERT INTO salary_payments_new 
                (id, user_id, role, amount_cents, payment_date, period_start, period_end, 
                 payment_type, comment, created_by_id, created_by_username, created_at)
                SELECT 
                    id, user_id, role, amount_cents, payment_date, period_start, period_end,
                    payment_type, comment, created_by_id, created_by_username, created_at
                FROM salary_payments
            ''')
            
            # Удаляем старую таблицу
            cursor.execute('DROP TABLE salary_payments')
            
            # Переименовываем новую таблицу
            cursor.execute('ALTER TABLE salary_payments_new RENAME TO salary_payments')
            
            # Восстанавливаем индексы
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_payments_user_id ON salary_payments(user_id, role)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_payments_date ON salary_payments(payment_date)')
            
            logger.info("Поле cash_transaction_id удалено")
        
        conn.commit()
        logger.info("Миграция 036_salary_payments_cash_transaction_link откачена")
