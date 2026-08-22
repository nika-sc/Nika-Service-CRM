"""Matching and text insert for diagnostics templates."""
from typing import Any, Dict, List, Optional


def _id_or_none(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def template_matches_device(
    row: Dict[str, Any],
    type_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    model_id: Optional[int] = None,
) -> bool:
    """A set template field must equal the device; NULL means «any»."""
    t_type = _id_or_none(row.get("device_type_id"))
    t_brand = _id_or_none(row.get("device_brand_id"))
    t_model = _id_or_none(row.get("model_id"))
    d_type = _id_or_none(type_id)
    d_brand = _id_or_none(brand_id)
    d_model = _id_or_none(model_id)
    if t_type is not None and t_type != d_type:
        return False
    if t_brand is not None and t_brand != d_brand:
        return False
    if t_model is not None and t_model != d_model:
        return False
    return True


def template_specificity(row: Dict[str, Any]) -> int:
    """Lower is more specific (model → brand → type → generic)."""
    if _id_or_none(row.get("model_id")) is not None:
        return 0
    if _id_or_none(row.get("device_brand_id")) is not None:
        return 1
    if _id_or_none(row.get("device_type_id")) is not None:
        return 2
    return 3


def rank_diagnostics_templates(
    rows: List[Dict[str, Any]],
    type_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    model_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Filter by device and sort: exact model, then brand/type, then generic."""
    matched = [
        row for row in (rows or [])
        if template_matches_device(row, type_id, brand_id, model_id)
    ]
    matched.sort(
        key=lambda row: (
            template_specificity(row),
            int(row.get("sort_order") or 0),
            int(row.get("id") or 0),
        )
    )
    return matched


def apply_diagnostics_template_text(current: Optional[str], template_body: str) -> str:
    """Empty field → insert template; non-empty → append after a blank line."""
    body = (template_body or "").replace("\r\n", "\n").strip("\n")
    existing = (current or "").replace("\r\n", "\n")
    if not existing.strip():
        return body
    return existing.rstrip() + "\n\n" + body
