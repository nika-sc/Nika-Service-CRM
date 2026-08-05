#!/usr/bin/env python3
"""Smoke: cache _to_json_safe round-trip (Redis type parity)."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.cache import _prepare_cache_value, _to_json_safe  # noqa: E402


class _OrderLike:
    def __init__(self) -> None:
        self.id = 7
        self.status_id = 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status_id": self.status_id,
            "created_at": datetime(2026, 8, 5, 12, 30, 0),
            "total": Decimal("2500.50"),
        }


def main() -> int:
    usage_shape = {
        "device_types": {"1": 3, "2": 0},
        "services": {"10": 5},
    }
    raw = {
        1: Decimal("1.25"),
        "when": date(2026, 8, 5),
        "order": _OrderLike(),
        "usage": usage_shape,
        "rows": [{"amt": Decimal("9"), "ts": datetime(2026, 1, 1, 0, 0, 0)}],
    }
    safe = _to_json_safe(raw)
    assert "1" in safe and safe["1"] == 1.25
    assert safe["when"] == "2026-08-05"
    assert safe["order"]["total"] == 2500.5
    assert isinstance(safe["order"]["created_at"], str)
    assert safe["usage"]["device_types"]["1"] == 3
    roundtrip = json.loads(json.dumps(safe, ensure_ascii=False))
    assert roundtrip == safe

    prepared, ok = _prepare_cache_value(raw)
    assert ok and prepared == safe

    class _Bad:
        pass

    bad, ok_bad = _prepare_cache_value(_Bad())
    assert not ok_bad and bad is None

    print("smoke_cache_json_safe: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
