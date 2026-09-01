"""Defensive security checks for Nika Service CRM (no exploit payloads, no live WORK)."""
import inspect
import json
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


def test_api_without_login_returns_401_not_login_redirect():
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    resp = client.get("/api/notifications/unread-count")
    assert resp.status_code == 401
    payload = resp.get_json() or {}
    assert payload.get("success") is False
    location = resp.headers.get("Location") or ""
    assert "/login" not in location


def test_login_rate_limit_decorator_skips_get():
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

    @main_mod.rate_limit_if_available("10 per minute", methods=("POST",))
    def ping():
        return "ok"

    app = create_app(_CsrfOffConfig)
    old = main_mod.limiter
    try:
        main_mod.limiter = FakeLimiter()
        with app.test_request_context("/login", method="GET"):
            assert ping() == "ok"
            assert calls == []
        with app.test_request_context("/login", method="POST", data={"username": "x"}):
            assert ping() == "ok"
            assert calls == ["10 per minute"]
    finally:
        main_mod.limiter = old


def test_sniff_client_upload_accepts_jpeg_png_pdf_rejects_mismatch():
    from app.utils.safe_files import sniff_client_upload

    assert sniff_client_upload(b"\xff\xd8\xff\xe0rest", "photo.jpg") == "image/jpeg"
    assert sniff_client_upload(b"\x89PNG\r\n\x1a\nrest", "shot.png") == "image/png"
    assert sniff_client_upload(b"%PDF-1.4 rest", "doc.pdf") == "application/pdf"
    assert sniff_client_upload(b"\xff\xd8\xff", "doc.pdf") is None
    assert sniff_client_upload(b"%PDF-1.4", "photo.jpg") is None
    assert sniff_client_upload(b"<svg></svg>", "x.svg") is None


def test_portal_public_order_strips_device_password():
    from app.routes.customer_portal import _portal_public_order

    out = _portal_public_order({
        "id": 1,
        "password": "secret-device",
        "diagnostics": "ok",
        "comment": "staff only",
    })
    assert "password" not in out
    assert "comment" not in out
    assert out["diagnostics"] == "ok"


def test_sniff_staff_upload_matches_magic_and_rejects_mismatch():
    from app.utils.safe_files import sniff_staff_upload

    assert sniff_staff_upload(b"\xff\xd8\xff\xe0rest", "photo.jpg") == "image/jpeg"
    assert sniff_staff_upload(b"PK\x03\x04rest", "archive.zip") is not None
    assert sniff_staff_upload(b"<html>not a jpeg", "photo.jpg") is None
    assert sniff_staff_upload(b"MZ\x90\x00fake", "notes.zip") is None
    assert sniff_staff_upload(b"%PDF-1.4 rest", "scan.pdf") == "application/pdf"


def test_settings_catalog_writes_use_manage_settings():
    src = (Path(__file__).resolve().parents[1] / "app" / "routes" / "settings.py").read_text(encoding="utf-8")
    assert "def catalog_access" in src
    assert '"manage_settings"' in src
    assert "@login_required" not in src
    assert src.count("@catalog_access") >= 25


def test_settings_save_error_hides_database_text():
    from app.routes.settings import settings_save_error
    from app.utils.exceptions import DatabaseError, ValidationError

    app = create_app(_CsrfOffConfig)
    with app.app_context():
        resp, code = settings_save_error(DatabaseError("ОШИБКА: столбец is_active имеет тип boolean"))
        assert code == 400
        payload = resp.get_json() or {}
        assert payload.get("success") is False
        assert "is_active" not in (payload.get("error") or "")
        assert "boolean" not in (payload.get("error") or "").lower()
        resp_ok, code_ok = settings_save_error(ValidationError("Название шаблона обязательно"))
        assert code_ok == 400
        assert "Название шаблона обязательно" in (resp_ok.get_json() or {}).get("error", "")


def test_invoice_static_requires_staff_session():
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    resp = client.get("/static/uploads/invoices/signature_audit.jpg")
    assert resp.status_code == 401
    payload = resp.get_json() or {}
    assert payload.get("error") == "auth_required"


def test_invoice_nginx_not_public_alias():
    root = Path(__file__).resolve().parents[1]
    nginx = (root / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    assert "location /static/uploads/invoices/" in nginx
    assert "proxy_pass http://backend;" in nginx
    assert "alias /var/www/nika/uploads/invoices/" not in nginx
    assert "map $http_x_forwarded_proto $fwd_proto" in nginx
    assert "X-Forwarded-Proto $fwd_proto" in nginx


def test_compose_security_env_and_beszel_bind():
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "CSP_NONCE_MODE=${CSP_NONCE_MODE:-report}" in compose
    assert "CSP_STRICT_ENFORCE_PREFIXES=${CSP_STRICT_ENFORCE_PREFIXES:-}" in compose
    assert "REDIS_PASSWORD" in compose
    monitoring = (root / "docker" / "docker-compose.monitoring.yml").read_text(encoding="utf-8")
    assert "--http=127.0.0.1:8090" in monitoring


def test_prod_requirements_exclude_pytest_playwright():
    root = Path(__file__).resolve().parents[1]
    prod = (root / "requirements.txt").read_text(encoding="utf-8")
    assert "pytest" not in prod
    assert "playwright" not in prod
    dev = (root / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "pytest" in dev
    assert "-r requirements.txt" in dev


def test_vendored_tinymce_is_patched():
    root = Path(__file__).resolve().parents[1]
    pkg = json.loads((root / "static" / "cdn" / "tinymce" / "latest" / "package.json").read_text(encoding="utf-8"))
    parts = [int(x) for x in str(pkg.get("version", "0")).split(".")[:3]]
    while len(parts) < 3:
        parts.append(0)
    assert tuple(parts) >= (8, 5, 1)


def test_socketio_disables_websocket_upgrade_outside_production():
    src = (Path(__file__).resolve().parents[1] / "app" / "__init__.py").read_text(encoding="utf-8")
    assert "allow_upgrades" in src


def test_portal_file_forbids_foreign_customer(monkeypatch):
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
    resp = client.get("/portal/api/order/5/file/1")
    assert resp.status_code == 403


def test_portal_api_requires_portal_session_not_staff_cookie():
    app = create_app(_CsrfOffConfig)
    resp = app.test_client().get("/portal/api/order/5")
    assert resp.status_code == 401


def test_safe_redirect_rejects_external_host():
    from app.utils.safe_redirect import is_safe_redirect_target

    app = create_app(_LanConfig)
    with app.test_request_context("/", headers={"Host": "127.0.0.1"}):
        assert is_safe_redirect_target("/orders") is True
        assert is_safe_redirect_target("https://evil.example/phish") is False
        assert is_safe_redirect_target("//evil.example/phish") is False


def test_validation_error_ignores_external_referrer():
    from app.utils.exceptions import ValidationError

    app = create_app(_CsrfOffConfig)

    def _raise_validation():
        raise ValidationError("нет")

    app.add_url_rule("/__sec_val", "sec_val_audit", _raise_validation)
    resp = app.test_client().get(
        "/__sec_val",
        headers={"Referer": "https://evil.example/phish"},
    )
    loc = resp.headers.get("Location") or ""
    assert "evil.example" not in loc


def test_invoice_asset_kind_whitelist():
    from app.routes.invoices import _invoice_asset_kind

    assert _invoice_asset_kind("logo") == "logo"
    assert _invoice_asset_kind("SIGNATURE") == "signature"
    assert _invoice_asset_kind("../stamp") is None
    assert _invoice_asset_kind("logo/../../x") is None


def test_write_api_limit_memory(monkeypatch):
    monkeypatch.setattr("app.utils.login_lockout._redis_client", lambda: None)
    from app.utils.write_api_limit import allow_write, reset_memory_for_tests

    reset_memory_for_tests()
    ip = "203.0.113.44"
    assert allow_write(ip, 2) is True
    assert allow_write(ip, 2) is True
    assert allow_write(ip, 2) is False


def test_staff_chat_disallows_archives():
    from app.services.staff_chat_service import _ALLOWED_EXTENSIONS

    assert "zip" not in _ALLOWED_EXTENSIONS
    assert "rar" not in _ALLOWED_EXTENSIONS
    assert "7z" not in _ALLOWED_EXTENSIONS
    assert "docx" in _ALLOWED_EXTENSIONS
    assert "xlsx" in _ALLOWED_EXTENSIONS


def test_safe_http_fetch_blocks_loopback_dns(monkeypatch):
    import socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port or 80))]

    monkeypatch.setattr("app.utils.safe_http_fetch.socket.getaddrinfo", fake_getaddrinfo)
    from app.utils.safe_http_fetch import fetch_public_http, is_safe_public_http_url

    assert is_safe_public_http_url("http://example.test/logo.png") is False
    assert fetch_public_http("http://example.test/logo.png") is None


def test_safe_http_fetch_accepts_public_dns(monkeypatch):
    import socket

    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port or 80))]

    monkeypatch.setattr("app.utils.safe_http_fetch.socket.getaddrinfo", fake_getaddrinfo)
    from app.utils.safe_http_fetch import is_safe_public_http_url

    assert is_safe_public_http_url("http://example.test/logo.png") is True
    assert is_safe_public_http_url("file:///etc/passwd") is False


def test_csp_strict_prefixes_enforce_nonce_on_login():
    class _StrictLogin(_LanConfig):
        CSP_NONCE_MODE = "report"
        CSP_REPORT_ONLY = True
        CSP_STRICT_ENFORCE_PREFIXES = ["/login"]

    app = create_app(_StrictLogin)
    resp = app.test_client().get("/login")
    csp = resp.headers.get("Content-Security-Policy") or ""
    assert "script-src 'self' 'nonce-" in csp
    assert "'unsafe-eval'" not in csp
    assert "'unsafe-inline'" not in csp or "style-src-attr 'unsafe-inline'" in csp
    # script-src must not keep legacy unsafe-inline
    assert "script-src 'self' 'unsafe-inline'" not in csp


def test_login_pages_include_csp_nonce_attr():
    root = Path(__file__).resolve().parents[1]
    staff = (root / "templates" / "auth" / "login.html").read_text(encoding="utf-8")
    portal = (root / "templates" / "portal" / "login.html").read_text(encoding="utf-8")
    assert 'nonce="{{ csp_nonce() }}"' in staff
    assert 'nonce="{{ csp_nonce() }}"' in portal


def test_staff_login_auth_fail_keeps_http_200(caplog):
    import logging

    app = create_app(_CsrfOffConfig)
    with caplog.at_level(logging.WARNING):
        resp = app.test_client().post(
            "/login",
            data={"username": "no-such-user-xyz", "password": "wrong-password-xyz"},
        )
    assert resp.status_code == 200
    assert "AUTH_FAIL" in caplog.text
    assert "kind=staff" in caplog.text


def test_portal_login_auth_fail_keeps_http_200(caplog):
    import logging

    app = create_app(_CsrfOffConfig)
    with caplog.at_level(logging.WARNING):
        resp = app.test_client().post(
            "/portal/login",
            data={"phone": "79001234567", "password": "wrong-password-xyz"},
        )
    assert resp.status_code == 200
    assert "AUTH_FAIL" in caplog.text
    assert "kind=portal" in caplog.text


def test_docker_runs_gunicorn_as_nika():
    root = Path(__file__).resolve().parents[1]
    dockerfile = (root / "docker" / "Dockerfile").read_text(encoding="utf-8")
    entry = (root / "docker" / "docker-entrypoint.sh").read_text(encoding="utf-8")
    compose = (root / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "gosu" in dockerfile
    assert "useradd" in dockerfile
    assert "exec gosu nika gunicorn" in entry
    assert "touch /app/logs/app.log" in entry
    assert "cap_drop" not in compose


def test_auth_fail_fail2ban_example_disabled_and_not_http_200():
    root = Path(__file__).resolve().parents[1]
    jail = (root / "deploy" / "hardening" / "fail2ban" / "jail.d" / "nika-auth-fail.local.example").read_text(
        encoding="utf-8"
    )
    filt = (root / "deploy" / "hardening" / "fail2ban" / "filter.d" / "nika-auth-fail.conf.example").read_text(
        encoding="utf-8"
    )
    login_filt = (root / "deploy" / "hardening" / "fail2ban" / "filter.d" / "nika-login.conf.example").read_text(
        encoding="utf-8"
    )
    assert "enabled = false" in jail
    assert "AUTH_FAIL" in filt
    assert "200" not in login_filt.split("failregex", 1)[-1]
    assert "(401|403|429)" in login_filt


def test_prod_requirements_pin_direct_security_stack():
    root = Path(__file__).resolve().parents[1]
    prod = (root / "requirements.txt").read_text(encoding="utf-8")
    assert "Flask~=3.1.3" in prod
    assert "Werkzeug~=3.1.8" in prod
    assert "bleach[css]~=6.1.0" in prod
    assert "gunicorn>=21.0.0,<23" in prod


def test_latest_blog_is_dashboard_owner_cash():
    from app.routes.public_blog import _POSTS

    assert _POSTS[0]["slug"] == "dashboard-owner-cash"
    assert _POSTS[0]["file"] == "blog/40-dashboard-owner-cash.md"
