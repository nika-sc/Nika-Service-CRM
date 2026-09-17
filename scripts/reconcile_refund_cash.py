#!/usr/bin/env python3
"""Снять с кассы исходный приход по уже сделанным полным возвратам.

Пример (WORK, в контейнере web):

  python scripts/reconcile_refund_cash.py --order-id 5581
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Сверка кассы после полного возврата оплаты")
    parser.add_argument("--order-id", type=int, help="Внутренний id заявки")
    parser.add_argument("--payment-id", type=int, help="Id исходной оплаты")
    parser.add_argument("--username", default="system", help="Кто выполняет сверку")
    args = parser.parse_args()

    from app import create_app
    from app.services.payment_service import PaymentService

    app = create_app()
    with app.app_context():
        n = PaymentService.reconcile_full_refund_cash(
            original_payment_id=args.payment_id,
            order_id=args.order_id,
            username=args.username,
            reason="Сверка: полный возврат снимает исходный приход",
        )
    print(f"voided_cash_rows={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
