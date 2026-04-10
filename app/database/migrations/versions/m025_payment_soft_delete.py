"""
Миграция 025: Soft-delete для оплат и кассовых операций.

Вместо физического удаления - помечаем записи как отменённые,
создаём сторно-операцию в кассе.
"""
import sqlite3


def up(conn: sqlite3.Connection):
    """Добавляем поля для soft-delete оплат и кассовых операций."""
    cursor = conn.cursor()
    
    # Добавляем поля в payments
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN is_cancelled INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Колонка уже существует
    
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN cancelled_at TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN cancelled_reason TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN cancelled_by_id INTEGER")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE payments ADD COLUMN cancelled_by_username TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Добавляем поля в cash_transactions
    try:
        cursor.execute("ALTER TABLE cash_transactions ADD COLUMN is_cancelled INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE cash_transactions ADD COLUMN cancelled_at TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE cash_transactions ADD COLUMN cancelled_reason TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE cash_transactions ADD COLUMN cancelled_by_id INTEGER")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE cash_transactions ADD COLUMN cancelled_by_username TEXT")
    except sqlite3.OperationalError:
        pass
    
    # Поле storno_of_id указывает на ID оригинальной операции (для сторно-записей)
    try:
        cursor.execute("ALTER TABLE cash_transactions ADD COLUMN storno_of_id INTEGER REFERENCES cash_transactions(id)")
    except sqlite3.OperationalError:
        pass
    
    # Индекс для быстрого поиска не-отменённых записей
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_payments_not_cancelled 
        ON payments(is_cancelled) WHERE is_cancelled = 0
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cash_transactions_not_cancelled 
        ON cash_transactions(is_cancelled) WHERE is_cancelled = 0
    """)
    
    conn.commit()


def down(conn: sqlite3.Connection):
    """Откат миграции - удаляем индексы (колонки в SQLite нельзя удалить)."""
    cursor = conn.cursor()
    
    cursor.execute("DROP INDEX IF EXISTS idx_payments_not_cancelled")
    cursor.execute("DROP INDEX IF EXISTS idx_cash_transactions_not_cancelled")
    
    conn.commit()

