"""Diagnostics templates: ranking, append, and modal markup."""
from pathlib import Path

from app.utils.diagnostics_templates import (
    apply_diagnostics_template_text,
    rank_diagnostics_templates,
)


def test_template_ranking_model_then_brand_then_generic():
    rows = [
        {"id": 1, "name": "generic", "sort_order": 1, "device_type_id": None, "device_brand_id": None, "model_id": None},
        {"id": 2, "name": "type", "sort_order": 1, "device_type_id": 10, "device_brand_id": None, "model_id": None},
        {"id": 3, "name": "brand", "sort_order": 1, "device_type_id": 10, "device_brand_id": 20, "model_id": None},
        {"id": 4, "name": "model", "sort_order": 1, "device_type_id": 10, "device_brand_id": 20, "model_id": 30},
        {"id": 5, "name": "other-brand", "sort_order": 1, "device_type_id": 10, "device_brand_id": 99, "model_id": None},
    ]
    ranked = rank_diagnostics_templates(rows, type_id=10, brand_id=20, model_id=30)
    assert [r["name"] for r in ranked] == ["model", "brand", "type", "generic"]


def test_template_ranking_falls_back_to_type_and_generic():
    rows = [
        {"id": 1, "name": "generic", "sort_order": 2, "device_type_id": None, "device_brand_id": None, "model_id": None},
        {"id": 2, "name": "ps", "sort_order": 1, "device_type_id": 4, "device_brand_id": None, "model_id": None},
        {"id": 3, "name": "phone", "sort_order": 1, "device_type_id": 1, "device_brand_id": None, "model_id": None},
    ]
    ranked = rank_diagnostics_templates(rows, type_id=4, brand_id=None, model_id=None)
    assert [r["name"] for r in ranked] == ["ps", "generic"]


def test_apply_template_inserts_when_empty():
    body = "Чистка, замена жидкого металла. Заключение мастера: перегрева нет."
    assert apply_diagnostics_template_text("  ", body) == body
    assert apply_diagnostics_template_text("", body) == body


def test_apply_template_appends_instead_of_overwrite():
    current = "Клиент жалуется на шум."
    body = "Чистка, продувка, тестирование."
    assert apply_diagnostics_template_text(current, body) == (
        "Клиент жалуется на шум.\n\nЧистка, продувка, тестирование."
    )


def test_diagnostics_modal_has_template_select():
    path = Path(__file__).resolve().parents[1] / "templates" / "partials" / "diagnostics_modal.html"
    html = path.read_text(encoding="utf-8")
    assert 'id="diagnosticsTemplateSelect"' in html


def test_is_active_uses_integer_zero_one():
    """Flags are INTEGER 0/1 like users/suppliers; SQL casts so bool binds still work."""
    import inspect

    from app.services.reference_service import ReferenceService

    assert ReferenceService._int_flag(True) == 1
    assert ReferenceService._int_flag(False) == 0
    assert ReferenceService._int_flag(1) == 1
    create_src = inspect.getsource(ReferenceService.create_diagnostics_template)
    update_src = inspect.getsource(ReferenceService.update_diagnostics_template)
    list_src = inspect.getsource(ReferenceService.list_diagnostics_templates)
    assert "CAST(? AS BIGINT)" in create_src
    assert "CAST(? AS BIGINT)" in update_src
    assert "_int_flag" in create_src
    assert "is_active = 1" in list_src
    assert "bool(is_active)" not in create_src
    assert "is_active = TRUE" not in list_src
