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
