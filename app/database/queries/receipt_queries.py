"""
SQL запросы для чеков (payment_receipts).
"""

from typing import Dict, List, Optional
import sqlite3
import logging

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class ReceiptQueries:
    @staticmethod
    def create_receipt(
        payment_id: int,
        receipt_type: str,
        status: str,
        provider: Optional[str] = None,
        provider_receipt_id: Optional[str] = None,
        payload: Optional[str] = None,
        response: Optional[str] = None,
        error: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None,
    ) -> int:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO payment_receipts (
                        payment_id, receipt_type, status,
                        provider, provider_receipt_id,
                        payload, response, error,
                        created_by_id, created_by_username
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payment_id, receipt_type, status,
                        provider, provider_receipt_id,
                        payload, response, error,
                        created_by_id, created_by_username,
                    ),
                )
                conn.commit()
                return int(cur.lastrowid)
        except Exception as e:
            logger.error(f"Ошибка при создании чека для payment_id={payment_id}: {e}", exc_info=True)
            raise

    @staticmethod
    def get_payment_receipts(payment_id: int) -> List[Dict]:
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT *
                    FROM payment_receipts
                    WHERE payment_id = ?
                    ORDER BY created_at DESC, id DESC
                    """,
                    (payment_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении чеков payment_id={payment_id}: {e}", exc_info=True)
            return []

    @staticmethod
    def get_receipt(receipt_id: int) -> Optional[Dict]:
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM payment_receipts WHERE id = ? LIMIT 1", (receipt_id,))
                row = cur.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении чека id={receipt_id}: {e}", exc_info=True)
            return None


