"""Money in words follows tenant currency units (RUB / KGS), without a live DB."""
from app.utils.money_words import amount_to_words_rub


def test_amount_to_words_rub_units(monkeypatch):
    monkeypatch.setattr(
        "app.utils.locale_fmt.get_money_word_units",
        lambda: {
            "major": ("рубль", "рубля", "рублей"),
            "minor": ("копейка", "копейки", "копеек"),
        },
    )
    text = amount_to_words_rub(1000.5)
    assert "рубл" in text.lower()
    assert "копе" in text.lower()
    assert "1000" not in text


def test_amount_to_words_kgs_units(monkeypatch):
    monkeypatch.setattr(
        "app.utils.locale_fmt.get_money_word_units",
        lambda: {
            "major": ("сом", "сома", "сомов"),
            "minor": ("тыйын", "тыйына", "тыйынов"),
        },
    )
    text = amount_to_words_rub(1000.5)
    assert "сом" in text.lower()
    assert "тыйын" in text.lower()
    assert "рубл" not in text.lower()
    assert "копе" not in text.lower()


def test_get_money_word_units_from_code(monkeypatch):
    from app.utils import locale_fmt

    monkeypatch.setattr(locale_fmt, "get_currency_code", lambda: "KGS")
    monkeypatch.setattr(locale_fmt, "get_money_symbol", lambda: "сом")
    units = locale_fmt.get_money_word_units()
    assert units["major"][0] == "сом"
    assert units["minor"][0] == "тыйын"

    monkeypatch.setattr(locale_fmt, "get_currency_code", lambda: "RUB")
    monkeypatch.setattr(locale_fmt, "get_money_symbol", lambda: "₽")
    units = locale_fmt.get_money_word_units()
    assert units["major"][0] == "рубль"
    assert units["minor"][0] == "копейка"
