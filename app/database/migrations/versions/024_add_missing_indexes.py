"""
Миграция 024: Добавление недостающих индексов.

Найдено при аудите базы данных:
- idx_cash_transactions_payment_id - для ускорения поиска по payment_id
- idx_cash_transactions_shop_sale_id - для ускорения поиска по shop_sale_id
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection) -> None:
    """Применить миграцию."""
    cursor = conn.cursor()
    
    # Индекс для cash_transactions.payment_id
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cash_transactions_payment_id 
        ON cash_transactions(payment_id)
    """)
    logger.info("Создан индекс idx_cash_transactions_payment_id")
    
    # Индекс для cash_transactions.shop_sale_id
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cash_transactions_shop_sale_id 
        ON cash_transactions(shop_sale_id)
    """)
    logger.info("Создан индекс idx_cash_transactions_shop_sale_id")
    
    conn.commit()
    logger.info("Миграция 024: индексы добавлены")


def down(conn: sqlite3.Connection) -> None:
    """Откатить миграцию."""
    cursor = conn.cursor()
    
    cursor.execute("DROP INDEX IF EXISTS idx_cash_transactions_payment_id")
    cursor.execute("DROP INDEX IF EXISTS idx_cash_transactions_shop_sale_id")
    
    conn.commit()
    logger.info("Миграция 024: индексы удалены")

