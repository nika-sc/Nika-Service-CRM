"""Tenant locale helpers: phone prefix and money symbol from general_settings.

Code defaults are Russia (prefix 7, symbol ₽, currency RUB). Per-server values
live in Postgres and are not hardcoded as a country fork.
"""
from __future__ import annotations

import re
from typing import List

_DEFAULT_PREFIX = "7"
_DEFAULT_SYMBOL = "₽"
_DEFAULT_CURRENCY = "RUB"


def _digits(value: str) -> str:
    return re.sub(r"\D", "", str(value or ""))


def get_phone_prefix() -> str:
    try:
        from app.services.settings_service import SettingsService

        raw = (SettingsService.get_general_settings() or {}).get("phone_prefix") or _DEFAULT_PREFIX
        digits = _digits(raw)
        return digits or _DEFAULT_PREFIX
    except Exception:
        return _DEFAULT_PREFIX


def get_currency_code() -> str:
    try:
        from app.services.settings_service import SettingsService

        raw = (SettingsService.get_general_settings() or {}).get("currency") or ""
        code = str(raw).strip().upper()
        if code in {"KGS", "SOM", "СОМ", "С"}:
            return "KGS"
        if code:
            return code
    except Exception:
        pass
    return _DEFAULT_CURRENCY


def get_money_symbol() -> str:
    try:
        from app.services.settings_service import SettingsService

        raw = (SettingsService.get_general_settings() or {}).get("currency_symbol")
        symbol = str(raw).strip() if raw is not None else ""
        symbol = symbol.replace("\\", "").replace("'", "").replace('"', "")
        return symbol or _DEFAULT_SYMBOL
    except Exception:
        return _DEFAULT_SYMBOL


def get_money_word_units() -> dict:
    """Russian inflections for major/minor currency units."""
    code = get_currency_code()
    symbol = (get_money_symbol() or "").strip().lower()
    if code == "RUB" or symbol in {"₽", "руб", "руб.", "рубль", "рубля", "рублей"}:
        return {
            "major": ("рубль", "рубля", "рублей"),
            "minor": ("копейка", "копейки", "копеек"),
        }
    if code == "KGS" or "сом" in symbol:
        return {
            "major": ("сом", "сома", "сомов"),
            "minor": ("тыйын", "тыйына", "тыйынов"),
        }
    if code == "KZT" or "тенге" in symbol:
        return {
            "major": ("тенге", "тенге", "тенге"),
            "minor": ("тиын", "тиына", "тиынов"),
        }
    fallback = get_money_symbol() or code or _DEFAULT_SYMBOL
    return {"major": (fallback, fallback, fallback), "minor": ("", "", "")}


def normalize_phone(phone: str) -> str:
    """Normalize a phone number using the tenant phone_prefix."""
    if not phone:
        return ""

    digits = _digits(phone)
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits:
        return ""

    prefix = get_phone_prefix()
    local_len = 10 if prefix == "7" else 9

    if prefix == "7":
        if (
            len(digits) == 12
            and digits[0] in "78"
            and digits[1] in "78"
            and digits[2] == "9"
        ):
            digits = "7" + digits[2:]
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        if digits and not digits.startswith("7"):
            digits = "7" + digits
        return digits

    if digits.startswith("0"):
        digits = digits.lstrip("0")
    if digits.startswith(prefix):
        return digits[: len(prefix) + local_len]
    return (prefix + digits)[: len(prefix) + local_len]


def format_phone_display(phone: str) -> str:
    if not phone:
        return ""
    digits = normalize_phone(phone)
    prefix = get_phone_prefix()
    if prefix == "7" and len(digits) == 11 and digits.startswith("7"):
        return f"+7({digits[1:4]}){digits[4:7]}-{digits[7:9]}-{digits[9:]}"
    if digits.startswith(prefix):
        rest = digits[len(prefix) :]
        if prefix == "996" and len(rest) == 9:
            return f"+{prefix} {rest[0:3]} {rest[3:6]} {rest[6:9]}"
        return "+" + digits
    return str(phone)


def phone_lookup_variants(phone: str) -> List[str]:
    raw = (phone or "").strip()
    digits = _digits(raw)
    normalized = normalize_phone(raw)
    prefix = get_phone_prefix()
    seen: List[str] = []
    for item in (raw, digits, normalized):
        if item and item not in seen:
            seen.append(item)
    if normalized.startswith(prefix) and len(normalized) > len(prefix):
        rest = normalized[len(prefix) :]
        extra = [
            rest,
            "+" + normalized,
            "+" + prefix + rest,
            format_phone_display(normalized),
        ]
        if prefix == "7" and len(normalized) >= 11:
            extra.extend(
                [
                    "8" + rest,
                    f"+7({rest[0:3]}){rest[3:6]}-{rest[6:8]}-{rest[8:10]}",
                    f"+7 ({rest[0:3]}) {rest[3:6]}-{rest[6:8]}-{rest[8:10]}",
                    f"8 ({rest[0:3]}) {rest[3:6]}-{rest[6:8]}-{rest[8:10]}",
                ]
            )
        for item in extra:
            if item and item not in seen:
                seen.append(item)
    return seen
