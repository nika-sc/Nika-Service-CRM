"""Phone locale: RF prefix 7 (default) and tenant prefix 996."""
from app.utils.locale_fmt import get_currency_code, get_money_symbol, get_phone_prefix
from app.utils.validators import normalize_phone, phone_lookup_variants


def test_locale_defaults_when_settings_unavailable(monkeypatch):
    def _boom():
        raise RuntimeError("no db")

    monkeypatch.setattr(
        "app.services.settings_service.SettingsService.get_general_settings",
        _boom,
    )
    assert get_phone_prefix() == "7"
    assert get_money_symbol() == "₽"
    assert get_currency_code() == "RUB"


def test_normalize_phone_kg_prefix(monkeypatch):
    monkeypatch.setattr("app.utils.locale_fmt.get_phone_prefix", lambda: "996")
    assert normalize_phone("700123456") == "996700123456"
    assert normalize_phone("+996 700 123 456") == "996700123456"
    assert normalize_phone("996700123456") == "996700123456"
    assert normalize_phone("0700123456") == "996700123456"


def test_phone_lookup_variants_kg(monkeypatch):
    monkeypatch.setattr("app.utils.locale_fmt.get_phone_prefix", lambda: "996")
    variants = phone_lookup_variants("+996 700 123 456")
    assert "996700123456" in variants
    assert "700123456" in variants
    assert "+996700123456" in variants
