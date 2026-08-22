"""Order customer email journal: titles, SQL flags, UI."""
from pathlib import Path

from app.routes.orders import format_phone_display, normalize_phone
from app.services.notification_service import NotificationService


def test_orders_module_keeps_phone_helpers():
    """format_phone_display must see module-level normalize_phone (not a replaced import)."""
    assert normalize_phone("8 (900) 111-22-33") == "79001112233"
    assert format_phone_display("79001112233") == "+7(900)111-22-33"


def test_customer_email_template_titles():
    assert NotificationService.customer_email_template_title("order_accepted") == "Заказ принят"
    assert NotificationService.customer_email_template_title("order_status_update") == "Смена статуса"
    assert NotificationService.customer_email_template_title("order_ready") == "Заказ готов"
    assert NotificationService.customer_email_template_title("order_closed_thanks") == "Заказ закрыт"


def test_record_customer_email_uses_integer_success():
    import inspect

    src = inspect.getsource(NotificationService.record_customer_email)
    assert "CAST(? AS BIGINT)" in src
    assert "1 if success else 0" in src


def test_order_detail_history_has_customer_emails_block():
    html = (Path(__file__).resolve().parents[1] / "templates" / "order_detail.html").read_text(
        encoding="utf-8"
    )
    assert 'id="orderCustomerEmails"' in html
    assert "Письма клиенту" in html


def test_bootstrap_marks_024():
    root = Path(__file__).resolve().parents[1]
    sql = (root / "app/database/migrations/postgres_versions/024_order_customer_emails.sql").read_text(
        encoding="utf-8"
    )
    assert "CREATE TABLE IF NOT EXISTS order_customer_emails" in sql
    assert "success BIGINT NOT NULL DEFAULT 0" in sql
    dump = (root / "database/bootstrap/nikacrm_public_sanitized.sql").read_text(encoding="utf-8")
    assert "024\torder_customer_emails" in dump
    assert "CREATE TABLE IF NOT EXISTS order_customer_emails" in dump
