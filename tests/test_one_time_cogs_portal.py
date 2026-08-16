"""Unit checks for one-time COGS, catalog helpers and portal sanitizer."""
import inspect
from pathlib import Path

from app.routes.customer_portal import sanitize_portal_order_lines, _is_ready_for_pickup
from app.routes.orders import add_order
from app.services.finance_service import FinanceService
from app.services.reference_service import ReferenceService


def test_sanitize_portal_hides_cost_and_executor():
    lines = sanitize_portal_order_lines([
        {
            "name": "Экран",
            "quantity": 1,
            "price": 3500,
            "purchase_price": 900,
            "cost_price": 100,
            "executor_id": 7,
            "executor_username": "master",
            "warranty_days": 30,
        }
    ])
    assert len(lines) == 1
    row = lines[0]
    assert row["name"] == "Экран"
    assert row["price"] == 3500
    assert row["warranty_days"] == 30
    assert "purchase_price" not in row
    assert "cost_price" not in row
    assert "executor_id" not in row
    assert "executor_username" not in row


def test_ready_for_pickup_by_status_name():
    assert _is_ready_for_pickup({"status_name": "Готов к выдаче", "is_final": 0}) is True
    assert _is_ready_for_pickup({"status_code": "ready", "is_final": False}) is True
    assert _is_ready_for_pickup({"status_name": "Готов к выдаче", "is_final": 1}) is False
    assert _is_ready_for_pickup({"status_name": "В работе"}) is False


def test_direct_cogs_category_constant():
    assert FinanceService.DIRECT_COGS_CATEGORY == "Себестоимость (разовая)"


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        self._cursor.committed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _EnsureCursor:
    def __init__(self, existing_id=None, insert_id=12):
        self.existing_id = existing_id
        self.lastrowid = insert_id
        self.committed = False
        self._last_sql = ""

    def execute(self, query, params=None):
        self._last_sql = query or ""

    def fetchone(self):
        sql = self._last_sql.lower()
        if "lower(name)" in sql:
            return (self.existing_id,) if self.existing_id else None
        if "max(sort_order)" in sql:
            return (4,)
        return None


class _CatalogCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""

    def execute(self, query, params=None):
        self.sql = query or ""

    def fetchall(self):
        return self.rows


def test_ensure_appearance_tag_returns_existing(monkeypatch):
    cursor = _EnsureCursor(existing_id=7)

    def _conn(*args, **kwargs):
        return _FakeConn(cursor)

    monkeypatch.setattr("app.services.reference_service.get_db_connection", _conn)
    tag_id = ReferenceService.ensure_appearance_tag("бывший в употреблении")
    assert tag_id == 7
    assert cursor.committed is False


def test_ensure_appearance_tag_creates_when_missing(monkeypatch):
    cursor = _EnsureCursor(existing_id=None, insert_id=21)

    def _conn(*args, **kwargs):
        return _FakeConn(cursor)

    monkeypatch.setattr("app.services.reference_service.get_db_connection", _conn)
    tag_id = ReferenceService.ensure_appearance_tag(ReferenceService.DEFAULT_USED_APPEARANCE_TAG)
    assert tag_id == 21
    assert cursor.committed is True


def test_ensure_appearance_tag_idempotent_constant():
    assert ReferenceService.DEFAULT_USED_APPEARANCE_TAG == "Бывший в употреблении"
    first = inspect.getsource(ReferenceService.ensure_appearance_tag)
    assert "LOWER(name)" in first
    assert "INSERT INTO appearance_tags" in first


def test_get_catalog_symptoms_returns_usage(monkeypatch):
    cursor = _CatalogCursor([
        {"id": 1, "name": "Не включается", "usage": 40},
        {"id": 2, "name": "Разбит экран", "usage": 12},
    ])

    def _conn(*args, **kwargs):
        return _FakeConn(cursor)

    monkeypatch.setattr("app.services.reference_service.get_db_connection", _conn)
    rows = ReferenceService.get_catalog_symptoms()
    assert rows[0]["name"] == "Не включается"
    assert rows[0]["usage"] == 40
    assert "order_symptoms" in cursor.sql
    assert "hidden" in cursor.sql


def test_add_order_pins_popular_and_default_bu():
    src = inspect.getsource(add_order)
    assert "ensure_appearance_tag" in src
    assert "DEFAULT_USED_APPEARANCE_TAG" in src
    root = Path(__file__).resolve().parents[1]
    html = (root / "templates" / "add_order.html").read_text(encoding="utf-8")
    assert "Частые" in html
    assert "Остальные" in html
    assert "Бывший в употреблении" in html
    assert "/api/catalog/symptoms" in html
    assert "CATALOG_TOP_N = 10" in html
    settings_src = (root / "app" / "routes" / "settings.py").read_text(encoding="utf-8")
    assert "/catalog/symptoms" in settings_src
