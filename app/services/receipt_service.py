"""
Сервис для чеков (payment_receipts).

Пока это "manual receipt" (печать/фиксация факта чека).
Интеграцию с фискальным провайдером можно добавить поверх (queued/sent/done/failed).
"""

from typing import Dict, List, Optional
from app.database.queries.receipt_queries import ReceiptQueries
from app.utils.exceptions import ValidationError, NotFoundError


class ReceiptService:
    @staticmethod
    def create_manual_receipt(
        payment_id: int,
        receipt_type: str,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None,
    ) -> int:
        if not payment_id or payment_id <= 0:
            raise ValidationError("Неверный ID оплаты")
        if receipt_type not in ("sell", "refund"):
            raise ValidationError("Неверный тип чека")

        receipt_id = ReceiptQueries.create_receipt(
            payment_id=payment_id,
            receipt_type=receipt_type,
            status="manual",
            provider=None,
            provider_receipt_id=None,
            payload=None,
            response=None,
            error=None,
            created_by_id=created_by_id,
            created_by_username=created_by_username,
        )
        return receipt_id

    @staticmethod
    def get_payment_receipts(payment_id: int) -> List[Dict]:
        if not payment_id or payment_id <= 0:
            raise ValidationError("Неверный ID оплаты")
        return ReceiptQueries.get_payment_receipts(payment_id)

    @staticmethod
    def get_receipt(receipt_id: int) -> Dict:
        if not receipt_id or receipt_id <= 0:
            raise ValidationError("Неверный ID чека")
        r = ReceiptQueries.get_receipt(receipt_id)
        if not r:
            raise NotFoundError("Чек не найден")
        return r


