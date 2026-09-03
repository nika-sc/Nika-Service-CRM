"""Refunds of receipts: admin only."""
from pathlib import Path

from app.utils.rbac import can_refund_receipts


def test_only_admin_can_refund_receipts():
    assert can_refund_receipts("admin") is True
    assert can_refund_receipts("manager") is False
    assert can_refund_receipts("master") is False
    assert can_refund_receipts("viewer") is False
    assert can_refund_receipts("manager_custom") is False
    assert can_refund_receipts("") is False


def test_order_refund_api_requires_admin():
    src = Path("app/routes/orders.py").read_text(encoding="utf-8")
    assert "can_refund_receipts" in src
    assert "check_role_permission(user_role, 'manager')" not in src.split("def api_refund_payment")[1][:800]


def test_shop_refund_and_delete_require_admin():
    src = Path("app/routes/shop.py").read_text(encoding="utf-8")
    refund_chunk = src.split("def api_refund_sale")[1][:500]
    delete_chunk = src.split("def api_delete_sale")[1][:500]
    assert "can_refund_receipts" in refund_chunk
    assert "can_refund_receipts" in delete_chunk


def test_ui_hides_refund_for_non_admin():
    order_html = Path("templates/order_detail.html").read_text(encoding="utf-8")
    shop_index = Path("templates/shop/index.html").read_text(encoding="utf-8")
    shop_detail = Path("templates/shop/sale_detail.html").read_text(encoding="utf-8")
    assert "current_user.role == 'admin'" in order_html
    assert "canRefundPayments" in order_html
    assert "current_user.role == 'admin'" in shop_index
    assert "current_user.role == 'admin'" in shop_detail
