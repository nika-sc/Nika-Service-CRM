"""Warehouse categories: create, rename, delete from the parts list."""
from pathlib import Path

from app.routes import warehouse as warehouse_routes
from app.services.warehouse_service import WarehouseService


def test_delete_category_api_returns_validation_error():
    src = Path("app/routes/warehouse.py").read_text(encoding="utf-8")
    chunk = src.split("def delete_category")[1][:900]
    assert "ValidationError" in chunk
    assert "api_internal_error" in chunk


def test_parts_list_has_visible_category_actions():
    pill = Path("templates/warehouse/_category_pill.html").read_text(encoding="utf-8")
    header = Path("templates/warehouse/parts_list.html").read_text(encoding="utf-8")
    assert "handleEditCategory" in pill
    assert "handleDeleteCategory" in pill
    assert "Новая категория" in header
    assert "has_permission('manage_warehouse')" in pill


def test_part_form_binds_new_category_by_id():
    src = Path("templates/warehouse/part_form.html").read_text(encoding="utf-8")
    assert "option.value = String(data.id)" in src
    assert 'option.value = name' not in src


def test_count_parts_in_category_uses_id():
    import inspect

    src = inspect.getsource(WarehouseService.delete_category)
    assert "count_parts_in_category(category_id" in src


def test_rename_updates_legacy_parts_category_column():
    src = Path("app/database/queries/warehouse_queries.py").read_text(encoding="utf-8")
    assert "UPDATE parts SET category = ?" in src
    assert "WHERE category_id = ?" in src


def test_delete_category_route_registered():
    assert hasattr(warehouse_routes, "delete_category")
    assert hasattr(warehouse_routes, "update_category")
    assert hasattr(warehouse_routes, "create_category")
