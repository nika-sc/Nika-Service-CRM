from __future__ import annotations

from datetime import timedelta
from typing import Optional, Tuple, Literal

from app.utils.datetime_utils import get_moscow_now


DefaultPeriod = Literal["today", "current_month", "last_7_days", "none"]


def normalize_date_range(
    date_from: Optional[str],
    date_to: Optional[str],
    default: DefaultPeriod = "none",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalizes (date_from, date_to) from request args.

    - If only one side is set, mirrors it to the other side.
    - If both are missing, applies a default preset when requested.
    """
    if date_from and not date_to:
        date_to = date_from
    if date_to and not date_from:
        date_from = date_to

    if not date_from and not date_to:
        now = get_moscow_now()
        today = now.date()
        if default == "today":
            today_str = today.strftime("%Y-%m-%d")
            date_from = today_str
            date_to = today_str
        elif default == "current_month":
            date_from = today.replace(day=1).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
        elif default == "last_7_days":
            date_from = (today - timedelta(days=6)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")

    return date_from, date_to

