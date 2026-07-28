"""
Миграция 066: привязка позиций счёта к каталогу и shop_sale при оплате без заявки.

- invoice_items.catalog_part_id / catalog_service_id
- invoices.shop_sale_id
"""
from __future__ import annotations

import logging

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def _table_columns(cursor, table: str) -> set:
    cursor.execute(f"PRAGMA table_info({table})")
    return {r[1] for r in cursor.fetchall()}


def _add_column_if_missing(cursor, table: str, column: str, ddl: str) -> None:
    cols = _table_columns(cursor, table)
    if column not in cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def upgrade():
    with get_db_connection() as conn:
        cur = conn.cursor()
        _add_column_if_missing(cur, "invoice_items", "catalog_part_id", "catalog_part_id INTEGER")
        _add_column_if_missing(cur, "invoice_items", "catalog_service_id", "catalog_service_id INTEGER")
        _add_column_if_missing(cur, "invoices", "shop_sale_id", "shop_sale_id INTEGER")
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoices_shop_sale_id ON invoices(shop_sale_id)"
        )
        conn.commit()
    logger.info("066_invoice_catalog_links: OK")


def downgrade():
    logger.info("066_invoice_catalog_links: downgrade skipped (columns kept)")
