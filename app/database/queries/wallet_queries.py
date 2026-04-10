"""
SQL запросы для кошелька клиента (customer_wallet_transactions).
"""

from typing import Dict, List, Optional
import sqlite3
import logging
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class WalletQueries:
    @staticmethod
    def get_customer_wallet_cents(customer_id: int) -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(wallet_cents, 0) FROM customers WHERE id = ?", (customer_id,))
            row = cur.fetchone()
            return int(row[0] or 0) if row else 0

    @staticmethod
    def update_customer_wallet_cents(customer_id: int, new_wallet_cents: int) -> None:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE customers SET wallet_cents = ? WHERE id = ?", (int(new_wallet_cents), customer_id))
            conn.commit()

    @staticmethod
    def add_wallet_transaction(
        customer_id: int,
        amount_cents: int,
        tx_type: str,
        source: str,
        order_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        comment: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None,
    ) -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO customer_wallet_transactions (
                    customer_id, amount_cents, tx_type, source,
                    order_id, payment_id, comment,
                    created_by_id, created_by_username
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    customer_id, int(amount_cents), tx_type, source,
                    order_id, payment_id, comment,
                    created_by_id, created_by_username,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    @staticmethod
    def get_wallet_transactions(customer_id: int, limit: int = 50) -> List[Dict]:
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT *
                    FROM customer_wallet_transactions
                    WHERE customer_id = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (customer_id, limit),
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении транзакций кошелька customer_id={customer_id}: {e}", exc_info=True)
            return []


