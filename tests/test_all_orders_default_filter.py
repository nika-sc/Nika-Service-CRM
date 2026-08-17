"""Default /all_orders filter is «Все в работе»."""
import inspect
from pathlib import Path

from app.routes.orders import _parse_all_orders_status, all_orders


def test_parse_all_orders_status():
    assert _parse_all_orders_status("in_progress") == "in_progress"
    assert _parse_all_orders_status("all") is None
    assert _parse_all_orders_status("") is None
    assert _parse_all_orders_status(None) is None
    assert _parse_all_orders_status(" closed ") == "closed"


def test_all_orders_defaults_to_in_progress():
    src = inspect.getsource(all_orders)
    assert "_redirect_all_orders_default_status" in src
    assert "_parse_all_orders_status" in src
    helper = inspect.getsource(__import__("app.routes.orders", fromlist=["_redirect_all_orders_default_status"])._redirect_all_orders_default_status)
    assert "in_progress" in helper
    root = Path(__file__).resolve().parents[1]
    sidebar = (root / "templates" / "partials" / "bootstrap_sidebar.html").read_text(encoding="utf-8")
    assert "status='in_progress'" in sidebar
    listing = (root / "templates" / "all_orders.html").read_text(encoding="utf-8")
    assert "status='all'" in listing
    assert "status=in_progress" in listing
