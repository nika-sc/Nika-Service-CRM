"""Russian phone login: 7 / +7 / 8 must resolve to the same number."""
from app.utils.validators import normalize_phone, phone_lookup_variants


def test_normalize_phone_accepts_7_plus7_and_8():
    expected = "79001261426"
    assert normalize_phone("79001261426") == expected
    assert normalize_phone("+79001261426") == expected
    assert normalize_phone("+7 900 126-14-26") == expected
    assert normalize_phone("+7 (900) 126-14-26") == expected
    assert normalize_phone("89001261426") == expected
    assert normalize_phone("8 (900) 126-14-26") == expected
    assert normalize_phone("9001261426") == expected


def test_normalize_phone_double_country_prefix():
    expected = "79001261426"
    # +7, затем вставили логин из письма 7900…
    assert normalize_phone("+779001261426") == expected
    assert normalize_phone("879001261426") == expected
    assert normalize_phone("789001261426") == expected


def test_phone_lookup_variants_cover_storage_formats():
    variants = phone_lookup_variants("+7 (900) 126-14-26")
    assert "79001261426" in variants
    assert "89001261426" in variants
    assert "9001261426" in variants
    assert "+79001261426" in variants
