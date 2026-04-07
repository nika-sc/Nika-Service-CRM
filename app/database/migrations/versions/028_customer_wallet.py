"""
Миграция 028: Кошелёк (депозит) клиента.

- customers.wallet_cents INTEGER NOT NULL DEFAULT 0
- customer_wallet_transactions: журнал операций по кошельку (источник истины)

Зачем:
- возврат "в депозит"
- оплата заявки с депозита (без движения денег по кассе)
"""

import logging
import sqlite3
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 028_customer_wallet")
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cur = conn.cursor()

        # customers.wallet_cents
        cur.execute("PRAGMA table_info(customers)")
        cols = [r[1] for r in cur.fetchall()]
        if "wallet_cents" not in cols:
            cur.execute("ALTER TABLE customers ADD COLUMN wallet_cents INTEGER NOT NULL DEFAULT 0")

        # Журнал операций
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS customer_wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL, -- + пополнение, - списание
                tx_type TEXT NOT NULL CHECK(tx_type IN ('credit', 'debit')),
                source TEXT NOT NULL DEFAULT 'manual' CHECK(source IN ('manual', 'refund', 'payment', 'adjustment')),
                order_id INTEGER,
                payment_id INTEGER,
                comment TEXT,
                created_by_id INTEGER,
                created_by_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id),
                FOREIGN KEY (created_by_id) REFERENCES users(id)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wallet_tx_customer_id ON customer_wallet_transactions(customer_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wallet_tx_order_id ON customer_wallet_transactions(order_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_wallet_tx_payment_id ON customer_wallet_transactions(payment_id)")

        conn.commit()
        logger.info("Миграция 028_customer_wallet применена")


def down():
    logger.warning("Откат 028_customer_wallet не поддерживается (SQLite DROP COLUMN ограничен)")


