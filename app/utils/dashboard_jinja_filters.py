"""
Форматирование дельт сводного отчёта (дашборд, письмо директору).
Ожидает dict от DashboardService.calculate_change.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _as_change_dict(change: Any) -> Optional[Dict[str, Any]]:
    if not change or not isinstance(change, dict):
        return None
    return change


def format_dashboard_money_change(change: Any) -> str:
    """Абсолютная разница в ₽ и процент со знаком, напр. «+1 950 ₽ (+52.5%)»."""
    ch = _as_change_dict(change)
    if ch is None:
        return "—"
    delta = float(ch.get("value") or 0)
    abs_part = f"{delta:+.0f} ₽"
    if ch.get("from_zero"):
        return f"{abs_part} (в сравн. периоде было 0)"
    sp = ch.get("signed_percent")
    if sp is None:
        return abs_part
    return f"{abs_part} ({float(sp):+.1f}%)"


def format_dashboard_count_change(change: Any) -> str:
    """Разница для счётчиков, напр. «+3 (+50.0%)»."""
    ch = _as_change_dict(change)
    if ch is None:
        return "—"
    delta = float(ch.get("value") or 0)
    iv = int(round(delta))
    abs_part = f"{iv:+d}"
    if ch.get("from_zero"):
        return f"{abs_part} (в сравн. периоде было 0)"
    sp = ch.get("signed_percent")
    if sp is None:
        return abs_part
    return f"{abs_part} ({float(sp):+.1f}%)"


def format_dashboard_avg_money_change(change: Any) -> str:
    """Средний чек: дельта в ₽ может быть дробной."""
    ch = _as_change_dict(change)
    if ch is None:
        return "—"
    delta = float(ch.get("value") or 0)
    if abs(delta - round(delta)) < 0.05:
        abs_part = f"{round(delta):+.0f} ₽"
    else:
        abs_part = f"{delta:+.2f} ₽"
    if ch.get("from_zero"):
        return f"{abs_part} (в сравн. периоде было 0)"
    sp = ch.get("signed_percent")
    if sp is None:
        return abs_part
    return f"{abs_part} ({float(sp):+.1f}%)"
