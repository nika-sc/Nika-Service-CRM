"""Defensive security checks for Nika Service CRM (no exploit payloads, no live WORK)."""
import inspect
import os
import tempfile
from pathlib import Path

import pytest

from app import create_app
from app.config import Config, ProductionConfig
from app.utils.error_handlers import (
    API_INTERNAL_ERROR_MESSAGE,
    LOGIN_RATE_LIMIT_MESSAGE,
    api_internal_error,
    rate_limit_http_response,
)
from app.utils.login_lockout import (
    clear,
    is_locked,
    register_failure,
    reset_memory_for_tests,
    seconds_until_unlock,
    user_lockout_message,
)
from app.utils.rbac import can_assign_user_role, can_create_role
from app.utils.safe_files import (
    confined_file_path,
    is_forbidden_upload_extension,
    mime_from_filename,
)
from app.services.salary_dashboard_service import _normalize_date_iso, _safe_sql_date
from app.services.settings_service import SettingsService


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


def test_outbound_mail_blocked_on_demo_banner():
    from app.services.notification_service import outbound_mail_blocked

    class _Demo:
        config = {"DEMO_LOGIN_BANNER": True, "MAIL_SENDING_ENABLED": True}

    class _Work:
        config = {"DEMO_LOGIN_BANNER": False, "MAIL_SENDING_ENABLED": True}

    class _ExplicitOff:
        config = {"DEMO_LOGIN_BANNER": False, "MAIL_SENDING_ENABLED": False}

    assert outbound_mail_blocked(_Demo()) is True
    assert outbound_mail_blocked(_Work()) is False
    assert outbound_mail_blocked(_ExplicitOff()) is True


def test_send_mail_retry_skips_smtp_when_blocked():
    from app.services import notification_service as ns

    class _Demo:
        config = {"DEMO_LOGIN_BANNER": True, "MAIL_TIMEOUT": 5}

    class _Mail:
        def send(self, _msg):
            raise AssertionError("SMTP must not be called on demo")

    assert ns._send_mail_with_retry(_Mail(), object(), _Demo()) is False


def test_show_portal_password_does_not_read_logs():
    from app.routes import customers as customers_mod

    src = inspect.getsource(customers_mod.api_show_portal_password)
    assert "generated_password" not in src
    assert "action_logs" not in src
    assert "plaintext" in src.lower() or "не хранится" in src.lower() or "сброс" in src.lower() or "Задайте" in src


def test_can_create_role_matrix():
    assert can_create_role("admin", "admin")
    assert can_create_role("admin", "manager")
    assert can_create_role("admin", "master")
    assert can_create_role("admin", "viewer")
    assert not can_create_role("manager", "admin")
    assert can_create_role("manager", "master")
    assert not can_create_role("manager", "viewer")
    assert can_create_role("manager_12", "master")
    assert not can_create_role("master", "master")
    assert not can_create_role("viewer", "viewer")


def test_can_assign_user_role_blocks_self_admin_escalation():
    assert can_assign_user_role(
        actor_role="manager",
        target_role="master",
        target_user_id=5,
        actor_user_id=5,
    )
    assert not can_assign_user_role(
        actor_role="manager",
        target_role="admin",
        target_user_id=5,
        actor_user_id=5,
    )


def test_mime_from_filename_ignores_client_type():
    assert mime_from_filename("photo.jpg") == "image/jpeg"
    assert mime_from_filename("doc.pdf") == "application/pdf"
    assert is_forbidden_upload_extension("icon.svg")
    assert mime_from_filename("icon.svg") == "application/octet-stream"


def test_save_print_template_refuses_without_sanitizer(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "app.utils.template_html_sanitizer":
            raise ImportError("no bleach")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert SettingsService.save_print_template("customer", "<script>x</script>") is False


def test_api_internal_error_hides_exception_text():
    app = create_app(_CsrfOffConfig)
    secret = "super-secret-db-password-leak"
    with app.app_context():
        resp, code = api_internal_error(RuntimeError(secret), "unit test")
    payload = resp.get_json()
    assert code == 500
    assert payload["error"] == API_INTERNAL_ERROR_MESSAGE
    assert secret not in payload["error"]


def test_routes_do_not_return_str_e_on_500():
    routes_dir = Path(__file__).resolve().parents[1] / "app" / "routes"
    offenders = []
    for path in routes_dir.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "str(e)" in line and ", 500" in line:
                offenders.append(f"{path.name}:{line.strip()}")
                break
    assert offenders == []


def test_login_rate_limit_renders_staff_form():
    app = create_app(_CsrfOffConfig)
    with app.test_request_context("/login", method="POST", data={"username": "tester"}):
        response = rate_limit_http_response()
        body = response.get_data(as_text=True)
        assert response.status_code == 429
        assert LOGIN_RATE_LIMIT_MESSAGE in body


def test_lockout_message_differs_from_rate_limit(monkeypatch):
    monkeypatch.setattr("app.utils.login_lockout._redis_client", lambda: None)
    reset_memory_for_tests()
    key = "203.0.113.9|locked"
    for _ in range(8):
        register_failure("staff", key)
    register_failure("staff", key)
    assert is_locked("staff", key)
    msg = user_lockout_message("staff", key)
    assert "через" in msg
    assert LOGIN_RATE_LIMIT_MESSAGE not in msg


def test_seconds_until_unlock_memory(monkeypatch):
    monkeypatch.setattr("app.utils.login_lockout._redis_client", lambda: None)
    reset_memory_for_tests()
    key = "203.0.113.10|ttl"
    for _ in range(8):
        register_failure("staff", key)
    register_failure("staff", key)
    assert seconds_until_unlock("staff", key) > 0
    clear("staff", key)
    assert seconds_until_unlock("staff", key) == 0


def test_comment_attachment_requires_view_orders(monkeypatch):
    import app.routes.comments as comments_mod

    class FakeUser:
        id = 7

    class FakeCursor:
        def execute(self, sql, params):
            self._sql = sql

        def fetchone(self):
            if "order_comments" in getattr(self, "_sql", ""):
                return {"order_id": 42}
            return None

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "app.routes.comments.UserService.check_permission",
        lambda user_id, perm: perm != "view_orders",
    )
    row = {"comment_id": 5, "filename": "a.pdf", "file_path": "x", "mime_type": "application/pdf"}
    assert not comments_mod.user_may_access_attachment(FakeCursor(), row, FakeUser.id)


def test_security_headers_include_coop_corp():
    app = create_app(_LanConfig)
    client = app.test_client()
    resp = client.get("/login")
    assert resp.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert resp.headers.get("Cross-Origin-Resource-Policy") == "same-site"
    assert resp.headers.get("X-Permitted-Cross-Domain-Policies") == "none"


def test_csp_nonce_mode_report_includes_strict_report_only():
    class _CspReportConfig(_LanConfig):
        CSP_NONCE_MODE = "report"
        CSP_REPORT_ONLY = True

    app = create_app(_CspReportConfig)
    client = app.test_client()
    resp = client.get("/login")
    ro = resp.headers.get("Content-Security-Policy-Report-Only") or ""
    assert "script-src 'self' 'nonce-" in ro
    assert "script-src 'self' 'unsafe-inline'" not in ro
    assert "script-src-attr 'none'" in ro


def test_csp_nonce_injected_on_request():
    app = create_app(_LanConfig)
    with app.test_request_context("/login"):
        app.preprocess_request()
        from flask import g
        nonce = getattr(g, "csp_nonce", None)
        assert nonce
        assert len(nonce) >= 8
