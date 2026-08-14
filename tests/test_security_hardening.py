"""Defensive security checks for Nika Service CRM (no exploit payloads, no live WORK)."""
import inspect
import os
import tempfile

import pytest

from app import create_app
from app.config import Config, ProductionConfig
from app.utils.login_lockout import clear, is_locked, register_failure, reset_memory_for_tests
from app.utils.safe_files import confined_file_path
from app.services.salary_dashboard_service import _normalize_date_iso, _safe_sql_date


class _LanConfig(Config):
    TESTING = True
    TRUSTED_HOSTS = ["localhost", "127.0.0.1", "@private"]
    WTF_CSRF_ENABLED = True
    RATELIMIT_ENABLED = False


class _CsrfOffConfig(Config):
    TESTING = True
    TRUSTED_HOSTS = ["localhost", "127.0.0.1"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


def test_lockout_memory_blocks_after_threshold(monkeypatch):
    monkeypatch.setattr("app.utils.login_lockout._redis_client", lambda: None)
    reset_memory_for_tests()
    key = "203.0.113.1|tester"
    for _ in range(7):
        assert not is_locked("staff", key)
        register_failure("staff", key)
    register_failure("staff", key)
    assert is_locked("staff", key)
    clear("staff", key)
    assert not is_locked("staff", key)


def test_safe_sql_date_rejects_non_iso():
    assert _safe_sql_date("2026-01-15", "1900-01-01") == "2026-01-15"
    assert _safe_sql_date("15.01.2026", "1900-01-01") == "1900-01-01"
    assert _safe_sql_date("2026-01-01'; DROP TABLE x;--", "1900-01-01") == "1900-01-01"
    assert _safe_sql_date("not-a-date", "2099-12-31") == "2099-12-31"
    assert _normalize_date_iso("2026-01-01'; DROP") is None
    assert _normalize_date_iso("2026-01-15") == "2026-01-15"


def test_confined_file_path_stays_in_root():
    with tempfile.TemporaryDirectory() as root:
        allowed = os.path.join(root, "ok.txt")
        with open(allowed, "w", encoding="utf-8") as fh:
            fh.write("ok")
        assert confined_file_path(allowed, root) == os.path.realpath(allowed)
        outside = os.path.join(root, "..", "escape.txt")
        assert confined_file_path(outside, root) is None
        assert confined_file_path(os.path.join(root, "..", "Windows", "win.ini"), root) is None


def test_staff_rate_limit_decorator_applies_at_runtime():
    import app.routes.main as main_mod

    calls = []

    class FakeLimiter:
        def limit(self, limit_str):
            def deco(f):
                def wrapped(*args, **kwargs):
                    calls.append(limit_str)
                    return f(*args, **kwargs)
                return wrapped
            return deco

    @main_mod.rate_limit_if_available("10 per minute")
    def ping():
        return "ok"

    old = main_mod.limiter
    try:
        main_mod.limiter = None
        assert ping() == "ok"
        assert calls == []
        main_mod.limiter = FakeLimiter()
        assert ping() == "ok"
        assert calls == ["10 per minute"]
    finally:
        main_mod.limiter = old


def test_production_empty_trusted_hosts_refuses_startup(monkeypatch):
    monkeypatch.setenv("TRUSTED_HOSTS", "")
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret-key-not-default-value-32")

    class _ProdEmpty(ProductionConfig):
        TESTING = False
        DEBUG = False
        TRUSTED_HOSTS = []
        SECRET_KEY = "unit-test-secret-key-not-default-value-32"

    with pytest.raises(ValueError, match="TRUSTED_HOSTS"):
        create_app(_ProdEmpty)


def test_csrf_login_post_without_token_rejected():
    app = create_app(_LanConfig)
    client = app.test_client()
    resp = client.post("/login", data={"username": "x", "password": "y"})
    assert resp.status_code in (400, 403)


def test_portal_order_api_forbids_foreign_order(monkeypatch):
    app = create_app(_CsrfOffConfig)

    def fake_full(order_id):
        return {"order": {"id": order_id, "customer_id": 999}}

    monkeypatch.setattr(
        "app.routes.customer_portal.OrderService.get_order_full_data",
        fake_full,
    )
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["portal_customer_id"] = 1
        sess["portal_customer_name"] = "Client"
    resp = client.get("/portal/api/order/5")
    assert resp.status_code == 403
    payload = resp.get_json() or {}
    assert payload.get("success") is False


def test_portal_session_cannot_open_staff_orders():
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["portal_customer_id"] = 1
    resp = client.get("/all_orders", follow_redirects=False)
    assert resp.status_code in (302, 401, 403)
    location = resp.headers.get("Location") or ""
    if resp.status_code == 302:
        assert "/login" in location


def test_search_special_chars_without_staff_login_not_500():
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    resp = client.get("/search", query_string={"q": "%_\\'\"<>"})
    assert resp.status_code != 500
    assert resp.status_code in (302, 401, 403)


def test_login_security_headers():
    app = create_app(_LanConfig)
    client = app.test_client()
    resp = client.get("/login")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "DENY"
    csp = resp.headers.get("Content-Security-Policy") or resp.headers.get(
        "Content-Security-Policy-Report-Only", ""
    )
    assert "frame-ancestors 'none'" in csp


def test_show_portal_password_does_not_read_logs():
    from app.routes import customers as customers_mod

    src = inspect.getsource(customers_mod.api_show_portal_password)
    assert "generated_password" not in src
    assert "action_logs" not in src
    assert "plaintext" in src.lower() or "не хранится" in src.lower() or "сброс" in src.lower() or "Задайте" in src
