"""Сумма прописью (рубли) для счетов/актов."""
from __future__ import annotations

_ONES = (
    "", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять",
    "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
    "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать",
)
_ONES_F = ("", "одна", "две")
_TENS = (
    "", "", "двадцать", "тридцать", "сорок", "пятьдесят",
    "шестьдесят", "семьдесят", "восемьдесят", "девяносто",
)
_HUNDREDS = (
    "", "сто", "двести", "триста", "четыреста", "пятьсот",
    "шестьсот", "семьсот", "восемьсот", "девятьсот",
)


def _triad(n: int, feminine: bool = False) -> str:
    n = int(n) % 1000
    if n == 0:
        return ""
    parts = []
    h, rem = divmod(n, 100)
    if h:
        parts.append(_HUNDREDS[h])
    if rem < 20:
        if rem:
            if feminine and rem in (1, 2):
                parts.append(_ONES_F[rem])
            else:
                parts.append(_ONES[rem])
    else:
        tens, ones = divmod(rem, 10)
        parts.append(_TENS[tens])
        if ones:
            if feminine and ones in (1, 2):
                parts.append(_ONES_F[ones])
            else:
                parts.append(_ONES[ones])
    return " ".join(parts)


def _plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n)) % 100
    if 11 <= n <= 19:
        return many
    n = n % 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def amount_to_words_rub(amount) -> str:
    """34000.5 -> «Тридцать четыре тысячи рублей 50 копеек»."""
    try:
        total_cents = int(round(float(amount) * 100))
    except (TypeError, ValueError):
        return ""
    total_cents = abs(total_cents)
    rub = total_cents // 100
    kop = total_cents % 100

    if rub == 0:
        words = "ноль"
    else:
        billions = rub // 1_000_000_000
        millions = (rub // 1_000_000) % 1000
        thousands = (rub // 1000) % 1000
        rest = rub % 1000
        chunks = []
        if billions:
            chunks.append(f"{_triad(billions)} {_plural(billions, 'миллиард', 'миллиарда', 'миллиардов')}")
        if millions:
            chunks.append(f"{_triad(millions)} {_plural(millions, 'миллион', 'миллиона', 'миллионов')}")
        if thousands:
            chunks.append(f"{_triad(thousands, feminine=True)} {_plural(thousands, 'тысяча', 'тысячи', 'тысяч')}")
        if rest:
            chunks.append(_triad(rest))
        words = " ".join(c.strip() for c in chunks if c.strip())

    words = (words[:1].upper() + words[1:]) if words else "Ноль"
    units = None
    try:
        from app.utils.locale_fmt import get_money_word_units

        units = get_money_word_units()
    except Exception:
        units = None
    major = (units or {}).get("major") or ("рубль", "рубля", "рублей")
    minor = (units or {}).get("minor") or ("копейка", "копейки", "копеек")
    if minor and minor[0]:
        return (
            f"{words} {_plural(rub, major[0], major[1], major[2])} "
            f"{kop:02d} {_plural(kop, minor[0], minor[1], minor[2])}"
        )
    return f"{words} {_plural(rub, major[0], major[1], major[2])}"


def cents_to_words_rub(cents: int) -> str:
    return amount_to_words_rub((cents or 0) / 100.0)


def format_money_rub(cents: int) -> str:
    val = (cents or 0) / 100.0
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", " ")
