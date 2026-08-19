"""Shop popular catalog and payment labels."""
from pathlib import Path

from app.routes.shop import payment_label_for
from app.services.finance_service import FinanceService


def test_payment_label_fallbacks():
    assert payment_label_for("") == "—"
    assert payment_label_for(None) == "—"
    assert payment_label_for("cash") == "Наличные"
    assert payment_label_for("card") == "Карта"
    assert payment_label_for("transfer") == "Перевод"
    assert payment_label_for("cash", [{"value": "cash", "label": "Нал."}]) == "Нал."
    assert payment_label_for("sbp", [{"value": "sbp", "label": "СБП"}]) == "СБП"


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _PopularCursor:
    def __init__(self):
        self.sql = ""

    def execute(self, query, params=None):
        self.sql = query or ""
        self.params = params

    def fetchall(self):
        if "JOIN services" in self.sql:
            return [(47, "Изготовление клише для автоматической оснастки", 1000, 12)]
        return [(8, "Trodat Printy 4642", "4642", 1000, 280, 5, 9)]


def test_popular_catalog_ranks_by_quantity(monkeypatch):
    cursor = _PopularCursor()

    def _conn(*args, **kwargs):
        return _FakeConn(cursor)

    monkeypatch.setattr("app.services.finance_service.get_db_connection", _conn)
    data = FinanceService.get_shop_popular_catalog(limit=10)
    assert data["services"][0]["id"] == 47
    assert data["services"][0]["type"] == "service"
    assert data["services"][0]["usage"] == 12
    assert data["parts"][0]["id"] == 8
    assert data["parts"][0]["stock_quantity"] == 5
    assert data["parts"][0]["out_of_stock"] is False
    assert "shop_sale_items" in cursor.sql
    assert "order_parts" in cursor.sql


def test_shop_template_has_popular_chips_and_checkout():
    html = (Path(__file__).resolve().parents[1] / "templates" / "shop" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "Частые услуги" in html
    assert "Частые товары" in html
    assert "Провести продажу" in html
    assert "shop.api_popular" in html
    assert "updatePrice" in html
    assert "print=1" in html
    assert "Укажите мастера" in html
    assert "Выберите мастера" in html


def test_required_shop_master_id_rejects_empty(monkeypatch):
    from app.routes.shop import required_shop_master_id
    from app.utils.exceptions import ValidationError

    for raw in (None, "", 0, "0"):
        try:
            required_shop_master_id(raw)
            assert False, raw
        except ValidationError as exc:
            assert "мастера" in str(exc)


def test_required_shop_master_id_rejects_unknown(monkeypatch):
    from app.routes.shop import required_shop_master_id
    from app.utils.exceptions import ValidationError

    class _Cur:
        def execute(self, *args, **kwargs):
            return None

        def fetchone(self):
            return None

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return _Cur()

    monkeypatch.setattr("app.routes.shop.get_db_connection", lambda: _Conn())
    try:
        required_shop_master_id(99)
        assert False
    except ValidationError as exc:
        assert "списка" in str(exc)

