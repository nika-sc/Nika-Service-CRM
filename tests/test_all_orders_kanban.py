"""Канбан /all_orders: доска цеха без авто-окна 7 дней."""
import inspect
from datetime import datetime
from pathlib import Path

from app.routes.orders import (
    _build_kanban_columns,
    _kanban_age_tone,
    _kanban_column_statuses,
    _order_age_days,
    all_orders,
)
from app.services.order_service import OrderService


ROOT = Path(__file__).resolve().parents[1]


def test_kanban_route_has_no_auto_seven_day_window():
    src = inspect.getsource(all_orders)
    assert "timedelta(days=6)" not in src
    assert "kanban_total" in src
    assert "sort_order='ASC'" in src
    assert "_KANBAN_MAX_ORDERS" in src or "150" in src


def test_get_orders_with_details_passes_sort_order():
    src = inspect.getsource(OrderService.get_orders_with_details)
    assert "sort_order" in src
    assert "sort_by" in src


def test_kanban_in_progress_keeps_empty_pipeline_columns():
    statuses = [
        {"id": 1, "code": "новый", "name": "Новый", "is_final": 0, "is_archived": 0},
        {"id": 2, "code": "closed", "name": "Закрыт", "is_final": 1, "is_archived": 0},
        {"id": 3, "code": "diag", "name": "Диагностика", "is_final": 0, "is_archived": 0},
        {"id": 4, "code": "unclaimed", "name": "Незабирашка", "is_final": 0, "is_archived": 0},
    ]
    cols = _kanban_column_statuses(statuses, "in_progress", [])
    ids = [c["id"] for c in cols]
    assert ids == [1, 3]
    columns = _build_kanban_columns(cols, [])
    assert [c["status"]["id"] for c in columns] == [1, 3]
    assert all(c["orders"] == [] for c in columns)


def test_kanban_specific_status_is_one_column():
    statuses = [
        {"id": 1, "code": "новый", "name": "Новый", "is_final": 0, "is_archived": 0},
        {"id": 3, "code": "diag", "name": "Диагностика", "is_final": 0, "is_archived": 0},
    ]
    cols = _kanban_column_statuses(statuses, "diag", [{"status_id": 1}])
    assert [c["id"] for c in cols] == [3]


def test_order_age_days_from_created(monkeypatch):
    class _Now:
        def date(self):
            return datetime(2026, 9, 19).date()

    monkeypatch.setattr("app.routes.orders.get_moscow_now", lambda: _Now())
    assert _order_age_days("2026-09-07 10:00:00") == 12
    assert _order_age_days(None) is None


def test_kanban_age_tone_scale():
    assert _kanban_age_tone(None) == "unknown"
    assert _kanban_age_tone(0) == "fresh"
    assert _kanban_age_tone(3) == "fresh"
    assert _kanban_age_tone(4) == "warn"
    assert _kanban_age_tone(6) == "warn"
    assert _kanban_age_tone(7) == "late"
    assert _kanban_age_tone(13) == "late"
    assert _kanban_age_tone(14) == "overdue"


def test_kanban_template_uses_static_board_assets():
    text = (ROOT / "templates" / "all_orders.html").read_text(encoding="utf-8")
    chunk = text.split("{% elif view == 'kanban' %}", 1)[1]
    chunk = chunk.split("{% block datatables_js %}", 1)[0]
    assert "css/orders-kanban.css" in text
    assert "js/orders-kanban.js" in text
    assert "NIKA_KANBAN" in text
    assert "kanban_shown" in chunk
    assert "phone_display" not in chunk
    assert "serial_number" not in chunk
    assert "onclick=\"window.location" not in chunk
    js = (ROOT / "static" / "js" / "orders-kanban.js").read_text(encoding="utf-8")
    assert "parseInt('ORDER_ID')" not in js
    assert "{{" not in js


def test_kanban_template_renders_empty_column():
    from flask import render_template

    from app import create_app
    from app.config import Config

    class _Cfg(Config):
        TESTING = True
        TRUSTED_HOSTS = ["localhost", "127.0.0.1"]
        WTF_CSRF_ENABLED = False
        RATELIMIT_ENABLED = False

    app = create_app(_Cfg)
    ctx = {
        "orders": [],
        "sort_by": "created_at",
        "sort_order": "ASC",
        "status_filter": "in_progress",
        "view": "kanban",
        "search_query": "",
        "manager_filter": None,
        "master_filter": None,
        "date_from": None,
        "date_to": None,
        "managers": [],
        "masters": [(1, "Сергей")],
        "order_statuses": [
            {"id": 3, "code": "diag", "name": "Диагностика", "color": "#0d6efd"},
        ],
        "status_map": {},
        "status_map_by_code": {},
        "status_dict": {},
        "status_counters": [],
        "active_status_counters": [],
        "archived_status_counters": [],
        "master_in_progress_counters": [],
        "total_orders": 0,
        "in_progress_orders_count": 0,
        "new_orders_count": 0,
        "in_progress_count": 0,
        "completed_count": 0,
        "closed_count": 0,
        "page": 1,
        "per_page": 150,
        "total": 0,
        "pages": 1,
        "close_print_mode": "choice",
        "kanban_total": 1,
        "kanban_shown": 1,
        "kanban_columns": [
            {
                "status": {"id": 3, "name": "Диагностика", "color": "#0d6efd"},
                "orders": [
                    {
                        "id": 42,
                        "client_name": "Клиент",
                        "device_line": "Kyocera M5521",
                        "age_days": 12,
                        "age_tone": "late",
                        "age_tone_label": "задержка",
                        "is_overdue": True,
                        "master_label": "Сергей",
                        "comments_count": 2,
                        "debt": 1500,
                        "prepayment": "",
                        "symptom_one": "не печатает",
                    }
                ],
            }
        ],
    }
    with app.test_request_context("/all_orders?view=kanban&status=in_progress"):
        html = render_template("all_orders.html", **ctx)
    assert "kanban-board" in html
    assert "Диагностика" in html
    assert "#42" in html
    assert "Kyocera M5521" in html
    assert "12 дн" in html
    assert "age-late" in html
    assert "kanban-legend" in html
    assert "is-overdue" not in html
    assert "orders-kanban.css" in html
    assert "orders-kanban.js" in html
    assert "/order/42" in html
    assert "phone_display" not in html
    assert "Показано 0 из" not in html
