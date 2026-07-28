"""SQL-запросы модуля счетов (B2B)."""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Dict, List, Optional, Any

from app.database.connection import get_db_connection
from app.utils.datetime_utils import get_moscow_now_naive

logger = logging.getLogger(__name__)


class InvoiceQueries:
    @staticmethod
    def next_number(doc_type: str, year: Optional[int] = None) -> int:
        year = year or get_moscow_now_naive().year
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO invoice_sequences (doc_type, year, last_number)
                VALUES (?, ?, 0)
                ON CONFLICT(doc_type, year) DO NOTHING
                """,
                (doc_type, year),
            )
            cur.execute(
                """
                UPDATE invoice_sequences
                SET last_number = last_number + 1
                WHERE doc_type = ? AND year = ?
                """,
                (doc_type, year),
            )
            cur.execute(
                """
                SELECT last_number FROM invoice_sequences
                WHERE doc_type = ? AND year = ?
                """,
                (doc_type, year),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row[0])

    @staticmethod
    def create_invoice(data: Dict[str, Any], items: List[Dict[str, Any]]) -> int:
        with get_db_connection() as conn:
            cur = conn.cursor()
            seller_snap = data.get("seller_snapshot")
            if isinstance(seller_snap, dict):
                seller_snap = json.dumps(seller_snap, ensure_ascii=False)
            cur.execute(
                """
                INSERT INTO invoices (
                    number, act_number, waybill_number, issued_at, due_date, status,
                    order_id, customer_id,
                    buyer_kind, buyer_name, buyer_inn, buyer_kpp, buyer_ogrn, buyer_address,
                    buyer_bank_name, buyer_bik, buyer_checking_account, buyer_corr_account,
                    seller_snapshot, subtotal_cents, vat_mode, total_cents, comment, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["number"],
                    data.get("act_number"),
                    data.get("waybill_number"),
                    data.get("issued_at") or get_moscow_now_naive().isoformat(sep=" ", timespec="seconds"),
                    data.get("due_date"),
                    data.get("status") or "unpaid",
                    data.get("order_id"),
                    data["customer_id"],
                    data.get("buyer_kind"),
                    data.get("buyer_name"),
                    data.get("buyer_inn"),
                    data.get("buyer_kpp"),
                    data.get("buyer_ogrn"),
                    data.get("buyer_address"),
                    data.get("buyer_bank_name"),
                    data.get("buyer_bik"),
                    data.get("buyer_checking_account"),
                    data.get("buyer_corr_account"),
                    seller_snap,
                    int(data.get("subtotal_cents") or 0),
                    data.get("vat_mode") or "none",
                    int(data.get("total_cents") or 0),
                    data.get("comment"),
                    data.get("created_by"),
                ),
            )
            invoice_id = int(cur.lastrowid)
            for idx, item in enumerate(items):
                cur.execute(
                    """
                    INSERT INTO invoice_items (
                        invoice_id, line_type, title, qty, unit, price_cents, sum_cents,
                        vat_label, source_order_service_id, source_order_part_id,
                        catalog_part_id, catalog_service_id, position
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        invoice_id,
                        item.get("line_type") or "service",
                        item["title"],
                        float(item.get("qty") or 1),
                        item.get("unit") or "шт",
                        int(item.get("price_cents") or 0),
                        int(item.get("sum_cents") or 0),
                        item.get("vat_label") or "Без НДС",
                        item.get("source_order_service_id"),
                        item.get("source_order_part_id"),
                        item.get("catalog_part_id") or item.get("part_id"),
                        item.get("catalog_service_id") or item.get("service_id"),
                        int(item.get("position", idx)),
                    ),
                )
            conn.commit()
            return invoice_id

    @staticmethod
    def get_invoice(invoice_id: int) -> Optional[Dict]:
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT i.*, c.name AS customer_name, c.phone AS customer_phone,
                       o.id AS order_ref
                FROM invoices i
                LEFT JOIN customers c ON c.id = i.customer_id
                LEFT JOIN orders o ON o.id = i.order_id
                WHERE i.id = ? AND COALESCE(i.is_deleted, 0) = 0
                """,
                (invoice_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            inv = dict(row)
            cur.execute(
                """
                SELECT * FROM invoice_items
                WHERE invoice_id = ?
                ORDER BY position, id
                """,
                (invoice_id,),
            )
            inv["items"] = [dict(r) for r in cur.fetchall()]
            if inv.get("seller_snapshot"):
                try:
                    inv["seller"] = json.loads(inv["seller_snapshot"])
                except Exception:
                    inv["seller"] = {}
            else:
                inv["seller"] = {}
            return inv

    @staticmethod
    def list_invoices(
        status: Optional[str] = None,
        search: Optional[str] = None,
        order_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict:
        page = max(1, int(page or 1))
        per_page = min(200, max(1, int(per_page or 50)))
        offset = (page - 1) * per_page
        where = ["COALESCE(i.is_deleted, 0) = 0"]
        params: List[Any] = []
        if status:
            where.append("i.status = ?")
            params.append(status)
        if order_id:
            where.append("i.order_id = ?")
            params.append(order_id)
        if search:
            q = f"%{search.strip()}%"
            where.append(
                "(CAST(i.number AS TEXT) LIKE ? OR i.buyer_name LIKE ? OR i.buyer_inn LIKE ? OR c.name LIKE ?)"
            )
            params.extend([q, q, q, q])
        where_sql = " AND ".join(where)
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT COUNT(*) FROM invoices i LEFT JOIN customers c ON c.id = i.customer_id WHERE {where_sql}",
                params,
            )
            total = int(cur.fetchone()[0])
            cur.execute(
                f"""
                SELECT i.*, c.name AS customer_name
                FROM invoices i
                LEFT JOIN customers c ON c.id = i.customer_id
                WHERE {where_sql}
                ORDER BY i.issued_at DESC, i.id DESC
                LIMIT ? OFFSET ?
                """,
                params + [per_page, offset],
            )
            items = [dict(r) for r in cur.fetchall()]
        pages = (total + per_page - 1) // per_page if per_page else 1
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    @staticmethod
    def update_status(
        invoice_id: int,
        status: str,
        *,
        paid_at=None,
        paid_by_user_id=None,
        payment_id=None,
        shop_sale_id=None,
    ) -> None:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE invoices
                SET status = ?,
                    paid_at = COALESCE(?, paid_at),
                    paid_by_user_id = COALESCE(?, paid_by_user_id),
                    payment_id = COALESCE(?, payment_id),
                    shop_sale_id = COALESCE(?, shop_sale_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND COALESCE(is_deleted, 0) = 0
                """,
                (status, paid_at, paid_by_user_id, payment_id, shop_sale_id, invoice_id),
            )
            conn.commit()

    @staticmethod
    def set_item_catalog_ids(item_id: int, *, catalog_part_id=None, catalog_service_id=None) -> None:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE invoice_items
                SET catalog_part_id = COALESCE(?, catalog_part_id),
                    catalog_service_id = COALESCE(?, catalog_service_id)
                WHERE id = ?
                """,
                (catalog_part_id, catalog_service_id, item_id),
            )
            conn.commit()

    @staticmethod
    def soft_delete(invoice_id: int) -> None:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE invoices
                SET is_deleted = 1, status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (invoice_id,),
            )
            conn.commit()
