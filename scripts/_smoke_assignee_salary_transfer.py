#!/usr/bin/env python3
"""Smoke: reassign master transfers salary accruals, then restore."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app import create_app
from app.database.connection import get_db_connection
from app.database.queries.salary_queries import SalaryQueries
from app.services.order_service import OrderService


def main() -> int:
    app = create_app()
    with app.app_context():
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT sa.order_id, o.master_id, o.manager_id
                FROM salary_accruals sa
                JOIN orders o ON o.id = sa.order_id
                WHERE sa.order_id IS NOT NULL AND sa.role = 'master'
                ORDER BY sa.order_id DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                print("NO_ACCRUAL_ORDERS")
                return 0
            oid, old_master, old_manager = int(row[0]), row[1], row[2]
            cur.execute(
                "SELECT id FROM masters WHERE id <> ? ORDER BY id LIMIT 1",
                (old_master or 0,),
            )
            alt = cur.fetchone()
            if not alt:
                print("NO_ALT_MASTER")
                return 0
            new_master = int(alt[0])

        print(f"order={oid} master {old_master} -> {new_master}")
        before = {
            a["user_id"]
            for a in SalaryQueries.get_accruals_for_order(oid)
            if a.get("role") == "master"
        }
        OrderService.update_order_assignees(
            oid,
            manager_id=int(old_manager) if old_manager is not None else None,
            master_id=new_master,
            username="smoke",
        )
        after = {
            a["user_id"]
            for a in SalaryQueries.get_accruals_for_order(oid)
            if a.get("role") == "master"
        }
        print("before", before, "after", after)
        assert after == {new_master}, after

        OrderService.update_order_assignees(
            oid,
            manager_id=int(old_manager) if old_manager is not None else None,
            master_id=int(old_master) if old_master is not None else None,
            username="smoke",
        )
        restored = {
            a["user_id"]
            for a in SalaryQueries.get_accruals_for_order(oid)
            if a.get("role") == "master"
        }
        print("restored", restored)
        print("SMOKE_OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
