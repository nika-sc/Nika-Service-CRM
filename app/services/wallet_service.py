"""
Сервис кошелька (депозита) клиента.

Правила:
- wallet_cents хранится в customers как быстрый баланс
- customer_wallet_transactions — журнал операций (источник истории)
- списание запрещено при недостатке средств
"""

from typing import Dict, List, Optional
from app.database.queries.wallet_queries import WalletQueries
from app.utils.exceptions import ValidationError, NotFoundError
from app.utils.cache import clear_cache
import sqlite3
from app.database.connection import get_db_connection


class WalletService:
    @staticmethod
    def get_balance(customer_id: int) -> Dict:
        if not customer_id or customer_id <= 0:
            raise ValidationError("Неверный ID клиента")
        cents = WalletQueries.get_customer_wallet_cents(customer_id)
        return {"customer_id": customer_id, "wallet_cents": cents, "wallet": cents / 100.0}

    @staticmethod
    def get_transactions(customer_id: int, limit: int = 50) -> List[Dict]:
        if not customer_id or customer_id <= 0:
            raise ValidationError("Неверный ID клиента")
        return WalletQueries.get_wallet_transactions(customer_id, limit)

    @staticmethod
    def credit(
        customer_id: int,
        amount: float,
        source: str = "manual",
        order_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        comment: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None,
    ) -> int:
        if amount is None:
            raise ValidationError("Не указана сумма")
        try:
            amount = float(amount)
        except Exception:
            raise ValidationError("Неверная сумма")
        if amount <= 0:
            raise ValidationError("Сумма должна быть больше нуля")
        amount_cents = int(round(amount * 100))

        return WalletService._apply(
            customer_id=customer_id,
            delta_cents=amount_cents,
            tx_type="credit",
            source=source,
            order_id=order_id,
            payment_id=payment_id,
            comment=comment,
            created_by_id=created_by_id,
            created_by_username=created_by_username,
        )

    @staticmethod
    def debit(
        customer_id: int,
        amount: float,
        source: str = "payment",
        order_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        comment: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None,
    ) -> int:
        if amount is None:
            raise ValidationError("Не указана сумма")
        try:
            amount = float(amount)
        except Exception:
            raise ValidationError("Неверная сумма")
        if amount <= 0:
            raise ValidationError("Сумма должна быть больше нуля")
        amount_cents = int(round(amount * 100))

        return WalletService._apply(
            customer_id=customer_id,
            delta_cents=-amount_cents,
            tx_type="debit",
            source=source,
            order_id=order_id,
            payment_id=payment_id,
            comment=comment,
            created_by_id=created_by_id,
            created_by_username=created_by_username,
        )

    @staticmethod
    def _apply(
        customer_id: int,
        delta_cents: int,
        tx_type: str,
        source: str,
        order_id: Optional[int],
        payment_id: Optional[int],
        comment: Optional[str],
        created_by_id: Optional[int],
        created_by_username: Optional[str],
    ) -> int:
        if not customer_id or customer_id <= 0:
            raise ValidationError("Неверный ID клиента")
        if delta_cents == 0:
            raise ValidationError("Нулевая сумма")
        if tx_type not in ("credit", "debit"):
            raise ValidationError("Неверный тип операции")

        # Транзакционно: читаем баланс, проверяем, пишем tx, обновляем баланс
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, COALESCE(wallet_cents, 0) FROM customers WHERE id = ?", (customer_id,))
            row = cur.fetchone()
            if not row:
                raise NotFoundError("Клиент не найден")
            current = int(row[1] or 0)
            new_balance = current + int(delta_cents)
            if new_balance < 0:
                raise ValidationError("Недостаточно средств на депозите клиента")

            # insert tx
            amount_cents = int(delta_cents)
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
                    customer_id, amount_cents, tx_type, source,
                    order_id, payment_id, comment,
                    created_by_id, created_by_username,
                ),
            )
            tx_id = int(cur.lastrowid)

            # update balance
            cur.execute("UPDATE customers SET wallet_cents = ? WHERE id = ?", (new_balance, customer_id))
            conn.commit()

        # cache
        clear_cache(key_prefix="customer")
        return tx_id


