"""Карточка заявки: slim GET без каталога parts/услуг и без SMTP-пароля."""
from pathlib import Path

from app import create_app
from app.config import Config
from app.database.connection import (
    clear_table_info_cache,
    get_table_info_cache,
    store_table_info_cache,
)
from app.services.reference_service import ReferenceService
from app.services.settings_service import SettingsService


class _CsrfOffConfig(Config):
    TESTING = True
    TRUSTED_HOSTS = ["localhost", "127.0.0.1"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


def test_public_general_settings_do_not_read_mail_password(monkeypatch):
    monkeypatch.setattr(
        SettingsService,
        "_get_general_settings_public",
        staticmethod(lambda: {"org_name": "СЦ", "mail_password": ""}),
    )
    calls = []
    monkeypatch.setattr(
        SettingsService,
        "get_mail_password",
        staticmethod(lambda: calls.append(1) or "SECRET"),
    )
    public = SettingsService.get_public_general_settings()
    assert public["org_name"] == "СЦ"
    assert public["mail_password"] == ""
    assert calls == []
    full = SettingsService.get_general_settings()
    assert full["mail_password"] == "SECRET"
    assert calls == [1]


def test_order_card_references_omit_heavy_catalogs(monkeypatch):
    monkeypatch.setattr(ReferenceService, "get_device_types", staticmethod(lambda: [{"id": 1}]))
    monkeypatch.setattr(ReferenceService, "get_device_brands", staticmethod(lambda: [{"id": 2}]))
    monkeypatch.setattr(ReferenceService, "get_managers", staticmethod(lambda: [{"id": 3}]))
    monkeypatch.setattr(ReferenceService, "get_masters", staticmethod(lambda: [{"id": 4}]))
    monkeypatch.setattr(ReferenceService, "get_symptoms", staticmethod(lambda: [{"id": 5}]))
    monkeypatch.setattr(ReferenceService, "get_appearance_tags", staticmethod(lambda: [{"id": 6}]))
    monkeypatch.setattr(ReferenceService, "get_order_statuses", staticmethod(lambda: [{"id": 7}]))
    usage_calls = []
    monkeypatch.setattr(
        ReferenceService,
        "get_all_usage_counts",
        staticmethod(lambda: usage_calls.append(1) or {"services": {}}),
    )
    refs = ReferenceService.get_order_card_references()
    assert refs["parts"] == []
    assert refs["order_models"] == []
    assert refs["services"] == []
    assert refs["managers"]
    assert usage_calls == []


def test_table_info_cache_roundtrip():
    clear_table_info_cache()
    store_table_info_cache("Payments", [(0, "id", "integer")])
    cached = get_table_info_cache("payments")
    assert cached[0][1] == "id"
    clear_table_info_cache()
    assert get_table_info_cache("payments") is None


def test_service_catalog_requires_login():
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    resp = client.get("/api/order/1/service-catalog")
    assert resp.status_code == 401
    payload = resp.get_json() or {}
    assert payload.get("success") is False


def test_order_detail_template_moved_assets_out_of_html():
    text = (Path(__file__).resolve().parents[1] / "templates" / "order_detail.html").read_text(encoding="utf-8")
    assert "all_services|tojson" not in text
    assert "js/order_detail/page.js" in text
    assert "css/order_detail.css" in text
    assert "<style nonce" not in text
    assert len(text.encode("utf-8")) < 250_000


def test_order_detail_page_js_does_not_post_nan_order_id():
    root = Path(__file__).resolve().parents[1] / "static" / "js" / "order_detail"
    leftovers = []
    for path in sorted(root.glob("*.js")):
        text = path.read_text(encoding="utf-8")
        if "parseInt('ORDER_ID')" in text or 'parseInt("ORDER_ID")' in text:
            leftovers.append(f"{path.name}: parseInt('ORDER_ID')")
        if "/from-order/ORDER_ID" in text:
            leftovers.append(f"{path.name}: /from-order/ORDER_ID")
        if "'ORDER_ID'" in text or '"ORDER_ID"' in text:
            leftovers.append(f"{path.name}: quoted ORDER_ID string")
        if "typeof ORDER_ID" in text:
            leftovers.append(f"{path.name}: typeof ORDER_ID")
        if "${ORDER_ID}" in text:
            leftovers.append(f"{path.name}: ${{ORDER_ID}} interpolation")
    assert leftovers == []


def test_extracted_js_has_no_leftover_jinja():
    root = Path(__file__).resolve().parents[1]
    leftovers = []
    for path in sorted((root / "static" / "js").rglob("*.js")):
        text = path.read_text(encoding="utf-8")
        if "{{" in text and "}}" in text:
            leftovers.append(str(path.relative_to(root)))
    assert leftovers == []


def test_inline_scripts_do_not_parseint_quoted_jinja_ids():
    """parseInt('{{ order.id }}') becomes parseInt('ORDER_ID') if JS is extracted."""
    root = Path(__file__).resolve().parents[1] / "templates"
    import re

    script_re = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)
    bad = re.compile(r"""parseInt\(\s*['"]\{\{[^}]+\}\}['"]|parseFloat\(\s*['"]\{\{[^}]+\}\}['"]""")
    leftovers = []
    for path in sorted(root.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for match in script_re.finditer(text):
            if re.search(r"\bsrc\s*=", match.group("attrs"), re.I):
                continue
            if bad.search(match.group("body")):
                leftovers.append(str(path.relative_to(root.parent)))
    assert leftovers == []


def test_order_detail_scripts_are_cache_busted():
    html = (Path(__file__).resolve().parents[1] / "templates" / "order_detail.html").read_text(
        encoding="utf-8"
    )
    assert "static_url('js/order_detail/page.js')" in html
    assert "static_url('js/order_detail/page_init.js')" in html
    from flask import render_template_string

    from app import create_app

    app = create_app(_CsrfOffConfig)
    with app.test_request_context():
        rendered = render_template_string("{{ static_url('js/order_detail/page.js') }}")
    assert "order_detail/page.js" in rendered
    assert "v=" in rendered
