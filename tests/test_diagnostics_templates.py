"""Diagnostics templates: ranking, replace, and modal markup."""
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


def test_apply_template_replaces_previous_text():
    current = "Диагностика подсветки, платы питания и главной платы."
    body = "Диагностика питания и портов, сброс и настройка."
    assert apply_diagnostics_template_text(current, body) == body
    assert apply_diagnostics_template_text("Клиент жалуется на шум.", body) == body


def test_diagnostics_modal_has_template_select():
    path = Path(__file__).resolve().parents[1] / "templates" / "partials" / "diagnostics_modal.html"
    html = path.read_text(encoding="utf-8")
    assert 'id="diagnosticsTemplateSearch"' in html
    assert 'id="diagnosticsTemplateList"' in html


def test_diagnostics_js_replaces_template_and_keeps_draft_on_upload():
    js = (Path(__file__).resolve().parents[1] / "static" / "js" / "order_detail" / "diagnostics.js").read_text(
        encoding="utf-8"
    )
    assert "preserveDraft" in js
    assert "uploadsInFlight" in js
    assert "pickTemplate" in js
    assert "filteredTemplates" in js
    assert "showSelectedTemplateName" in js
    assert "existing.replace" not in js
    assert "selectedIndex = 0" not in js


def test_settings_template_loads_device_catalog_after_dom_ready():
    path = Path(__file__).resolve().parents[1] / "templates" / "settings.html"
    html = path.read_text(encoding="utf-8")
    assert "bindDiagnosticsTemplateCatalog" in html
    assert "fetch('/api/device-types')" in html
    assert "fetch('/api/order-models')" in html
    assert 'id="diagnostics-templates-tab"' in html
    assert 'data-bs-target="#diagnostics-templates"' in html
    assert "loadDiagnosticsTemplatesTable" in html


def test_seed_and_bootstrap_mark_022_023():
    root = Path(__file__).resolve().parents[1]
    seed = (root / "app/database/migrations/postgres_versions/023_diagnostics_templates_seed.sql").read_text(
        encoding="utf-8"
    )
    assert "PS5 — чистка с заменой жидкого металла" in seed
    assert "WHERE NOT EXISTS" in seed
    alter = (root / "app/database/migrations/postgres_versions/022_diagnostics_templates_is_active_int.sql").read_text(
        encoding="utf-8"
    )
    assert "TYPE BIGINT" in alter
    dump = (root / "database/bootstrap/nikacrm_public_sanitized.sql").read_text(encoding="utf-8")
    assert "022\tdiagnostics_templates_is_active_int" in dump
    assert "023\tdiagnostics_templates_seed" in dump
    assert "is_active BIGINT NOT NULL DEFAULT 1" in dump


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
