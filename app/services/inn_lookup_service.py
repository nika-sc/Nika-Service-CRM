"""Сервис автозаполнения реквизитов по ИНН (DaData, опционально)."""
from __future__ import annotations

import json
import logging
import urllib.request
from typing import Dict

from app.database.connection import get_db_connection
from app.services.settings_service import SettingsService
from app.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


class InnLookupService:
    @staticmethod
    def get_api_token() -> str:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT value FROM system_settings WHERE key = ?",
                    ("dadata_api_token",),
                )
                row = cur.fetchone()
                if row:
                    return (row[0] or "").strip()
        except Exception as e:
            logger.debug("dadata token read failed: %s", e)
        return ""

    @staticmethod
    def save_api_token(token: str) -> None:
        with get_db_connection() as conn:
            cur = conn.cursor()
            SettingsService._upsert_system_settings(
                cur,
                [
                    (
                        "dadata_api_token",
                        (token or "").strip(),
                        "DaData API token для поиска по ИНН",
                    )
                ],
            )
            conn.commit()

    @staticmethod
    def lookup(inn: str) -> Dict:
        inn = "".join(ch for ch in (inn or "") if ch.isdigit())
        if len(inn) not in (10, 12):
            raise ValidationError("ИНН должен содержать 10 или 12 цифр")

        token = InnLookupService.get_api_token()
        if not token:
            raise ValidationError(
                "Автозаполнение по ИНН не настроено. Укажите токен DaData в Счета → Настройки "
                "или заполните реквизиты вручную."
            )

        payload = json.dumps({"query": inn}).encode("utf-8")
        req = urllib.request.Request(
            "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Token {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning("DaData lookup failed: %s", e)
            raise ValidationError(
                "Не удалось получить данные по ИНН. Введите реквизиты вручную."
            )

        suggestions = (data or {}).get("suggestions") or []
        if not suggestions:
            raise ValidationError("Организация с таким ИНН не найдена")

        item = suggestions[0]
        d = item.get("data") or {}
        addr = ""
        if isinstance(d.get("address"), dict):
            addr = d["address"].get("unrestricted_value") or d["address"].get("value") or ""
        elif isinstance(d.get("address"), str):
            addr = d.get("address") or ""

        party_type = (d.get("type") or "").upper()
        kind = "ip" if party_type == "INDIVIDUAL" or len(inn) == 12 else "legal"
        name = (
            (d.get("name") or {}).get("full_with_opf")
            or (d.get("name") or {}).get("short_with_opf")
            or item.get("value")
            or ""
        )
        return {
            "inn": d.get("inn") or inn,
            "kpp": d.get("kpp") or "",
            "ogrn": d.get("ogrn") or "",
            "name": name,
            "legal_name": name,
            "legal_address": addr,
            "customer_kind": kind,
            "type": kind,
        }
