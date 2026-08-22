#!/usr/bin/env python3
"""
Сторно начислений зарплаты, ошибочно созданных при открытии карточки заявки (GET /order/...).

Инцидент: при просмотре заявок из поиска срабатывал пересчёт зарплаты в order_detail,
из-за чего в salary_accruals появлялись новые строки с «сегодняшней» датой.

Использование (из корня репозитория, с настроенным .env / переменными БД):

  # просмотр, что будет удалено
  python scripts/storno_salary_accruals_order_view_glitch.py --dry-run

  # выполнить удаление начислений + связанных system-логов action_logs
  python scripts/storno_salary_accruals_order_view_glitch.py --execute

Параметры по умолчанию соответствуют типичному окну инцидента 2026-04-24 ~13:58–13:59
и списку заявок клиента 29 (МРТ), которые попали в пакетный пересчёт.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from app.database.connection import get_db_connection  # noqa: E402


DEFAULT_ORDER_IDS = (
    865,
    2735,
    2890,
    3076,
    3218,
    4373,
    4458,
    4745,
    4816,
    4871,
)
DEFAULT_SINCE = "2026-04-24 13:58:00"
DEFAULT_UNTIL = "2026-04-24 14:05:00"


def _parse_order_ids(raw: str | None) -> Tuple[int, ...]:
    if not raw or not str(raw).strip():
        return DEFAULT_ORDER_IDS
    out: List[int] = []
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return tuple(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--order-ids",
        type=str,
        default="",
        help="Список id заявок через запятую (по умолчанию — фиксированный набор инцидента)",
    )
    parser.add_argument("--since", type=str, default=DEFAULT_SINCE, help="Нижняя граница created_at (включительно)")
    parser.add_argument("--until", type=str, default=DEFAULT_UNTIL, help="Верхняя граница created_at (исключительно)")
    parser.add_argument("--dry-run", action="store_true", help="Только показать строки, без удаления")
    parser.add_argument("--execute", action="store_true", help="Выполнить удаление")
    args = parser.parse_args()

    if args.execute and args.dry_run:
        print("Укажите только один из флагов: --execute или --dry-run")
        return 2
    if not args.execute and not args.dry_run:
        print("Укажите --dry-run или --execute")
        return 2

    order_ids = _parse_order_ids(args.order_ids)
    placeholders = ",".join("?" * len(order_ids))

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, order_id, user_id, role, amount_cents, created_at
            FROM salary_accruals
            WHERE order_id IN ({placeholders})
              AND created_at >= ?
              AND created_at < ?
            ORDER BY order_id, id
            """,
            (*order_ids, args.since, args.until),
        )
        rows = cur.fetchall()
        print(f"Найдено записей salary_accruals: {len(rows)}")
        for r in rows:
            print(f"  id={r[0]} order_id={r[1]} user_id={r[2]} role={r[3]} amount_cents={r[4]} created_at={r[5]}")

        cur.execute(
            f"""
            SELECT id, created_at, username, entity_type, entity_id
            FROM action_logs
            WHERE entity_type = 'salary_accrual'
              AND entity_id IN ({placeholders})
              AND created_at >= ?
              AND created_at < ?
            ORDER BY id
            """,
            (*order_ids, args.since, args.until),
        )
        logs = cur.fetchall()
        print(f"Найдено записей action_logs (salary_accrual): {len(logs)}")
        for r in logs:
            print(f"  log id={r[0]} created_at={r[1]} username={r[2]} entity_id={r[4]}")

        if args.dry_run:
            return 0

        cur.execute(
            f"""
            DELETE FROM salary_accruals
            WHERE order_id IN ({placeholders})
              AND created_at >= ?
              AND created_at < ?
            """,
            (*order_ids, args.since, args.until),
        )
        deleted_sa = cur.rowcount

        cur.execute(
            f"""
            DELETE FROM action_logs
            WHERE entity_type = 'salary_accrual'
              AND entity_id IN ({placeholders})
              AND created_at >= ?
              AND created_at < ?
            """,
            (*order_ids, args.since, args.until),
        )
        deleted_logs = cur.rowcount

        conn.commit()
        print(f"Удалено salary_accruals: {deleted_sa}")
        print(f"Удалено action_logs: {deleted_logs}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
