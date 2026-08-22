"""Render order print templates (receipt, sales receipt, work act)."""
from __future__ import annotations

import html as _html
import logging
import re
from datetime import datetime as _dt
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from flask import request, url_for

from app.services.settings_service import SettingsService
from app.utils.print_template_renderer import render_print_template

logger = logging.getLogger(__name__)


def _safe(value: Any) -> str:
    return _html.escape("" if value is None else str(value))


def _line_discount(price: float, qty: int, discount_type: str, discount_val: float) -> float:
    if discount_type == "percent" and discount_val:
        return round(price * qty * discount_val / 100.0, 2)
    if discount_type == "fixed":
        return min(round(discount_val * qty, 2), round(price * qty, 2))
    return 0.0


def render_order_print_templates(
    *,
    order,
    order_data: Dict[str, Any],
    settings: Dict[str, Any],
    totals: Dict[str, Any],
    order_services: list,
    order_parts: list,
    amount_to_words=None,
) -> Dict[str, Optional[str]]:
    """Return rendered HTML for customer / sales_receipt / work_act (or None)."""
    result = {"customer": None, "sales_receipt": None, "work_act": None}
    try:
        tpl = SettingsService.get_print_template("customer")
        html_content = (tpl or {}).get("html_content") if isinstance(tpl, dict) else None
        sales_tpl = SettingsService.get_print_template("sales_receipt")
        sales_html = (sales_tpl or {}).get("html_content") if isinstance(sales_tpl, dict) else None
        work_tpl = SettingsService.get_print_template("work_act")
        work_html = (work_tpl or {}).get("html_content") if isinstance(work_tpl, dict) else None
        if not any(
            isinstance(chunk, str) and chunk.strip()
            for chunk in (html_content, sales_html, work_html)
        ):
            return result

        order_obj = order_data.get("order") or {}
        customer_obj = order_data.get("customer") or {}
        device_obj = order_data.get("device") or {}
        try:
            logo_max_width = int(settings.get("logo_max_width") or 320)
        except (TypeError, ValueError):
            logo_max_width = 320
        try:
            logo_max_height = int(settings.get("logo_max_height") or 120)
        except (TypeError, ValueError):
            logo_max_height = 120

        raw_logo_url = (settings.get("logo_url") or "").strip()
        if raw_logo_url and re.match(r"^https?://", raw_logo_url, flags=re.IGNORECASE):
            logo_url = url_for("orders.print_logo_proxy", _external=True)
        elif raw_logo_url:
            logo_url = urljoin(request.url_root, raw_logo_url.lstrip("/"))
        else:
            logo_url = raw_logo_url

        now = _dt.now()
        values = {
            "COMPANY_NAME": _safe(settings.get("org_name") or ""),
            "branch.address": _safe(settings.get("address") or ""),
            "branch.phone": _safe(settings.get("phone") or ""),
            "COMPANY_REQUISITES": _safe(" ".join([
                p for p in [
                    f"ИНН: {settings.get('inn')}" if settings.get("inn") else "",
                    f"ОГРН: {settings.get('ogrn')}" if settings.get("ogrn") else "",
                ] if p
            ]).strip()),
            "ORDER_NUMBER": _safe(f"#{order_obj.get('id')}" if order_obj.get("id") else ""),
            "ORDER_ID": _safe(order_obj.get("id") or ""),
            "ORDER_UUID": _safe(order_obj.get("order_id") or ""),
            "STATUS_NAME": _safe(order_obj.get("status_name") or ""),
            "CLIENT_NAME": _safe(order_obj.get("client_name") or customer_obj.get("name") or ""),
            "CLIENT_PHONE1": _safe(
                order_obj.get("phone_display")
                or order_obj.get("phone")
                or customer_obj.get("phone_display")
                or customer_obj.get("phone")
                or ""
            ),
            "CLIENT_PHONE": _safe(order_obj.get("phone") or customer_obj.get("phone") or ""),
            "CLIENT_EMAIL": _safe(order_obj.get("email") or customer_obj.get("email") or ""),
            "TOTAL_PAID": _safe(
                f"{totals.get('paid', 0):.2f}"
                if isinstance(totals, dict) and totals.get("paid")
                else "0.00"
            ),
            "ENGINEER_NAME": _safe(order_obj.get("master_name") or ""),
            "MASTER_NAME": _safe(order_obj.get("master_name") or ""),
            "MANAGER_NAME": _safe(order_obj.get("manager_name") or ""),
            "CURRENCY": _safe("₽"),
            "EMPLOYEE_NAME": _safe(order_obj.get("master_name") or order_obj.get("manager_name") or ""),
            "COMPANY_LOGO_URL": _safe(logo_url),
            "COMPANY_LOGO_STYLE": _safe(
                f"max-width: {logo_max_width}px; max-height: {logo_max_height}px; width: auto; height: auto;"
            ),
            "DATE_TODAY": _safe(now.strftime("%d.%m.%Y")),
            "TIME_NOW": _safe(now.strftime("%H:%M")),
            "MODEL": _safe(order_obj.get("model") or ""),
            "COMMENT": _safe(order_obj.get("comment") or ""),
            "DEVICE_TYPE": _safe(order_obj.get("device_type_name") or device_obj.get("device_type") or ""),
            "DEVICE_BRAND": _safe(order_obj.get("device_brand_name") or device_obj.get("device_brand") or ""),
            "SERIAL_NUMBER": _safe(order_obj.get("serial_number") or device_obj.get("serial_number") or ""),
            "SYMPTOM_TAGS": _safe(order_obj.get("symptom_tags") or ""),
            "APPEARANCE": _safe(order_obj.get("appearance") or ""),
            "PASSWORD": _safe(order_obj.get("password") or ""),
        }

        print_items = []
        total_items_sum = 0.0
        for idx, row in enumerate(order_services or [], 1):
            qty = int(row.get("quantity") or 1)
            price = float(row.get("price") or row.get("service_price") or 0)
            discount_amount = _line_discount(
                price, qty, (row.get("discount_type") or "").strip().lower(),
                float(row.get("discount_value") or 0),
            )
            row_sum = round(price * qty - discount_amount, 2)
            total_items_sum += row_sum
            print_items.append({
                "INDEX": _safe(str(idx)),
                "ITEM_NAME": _safe(row.get("name") or row.get("service_name") or ""),
                "ITEM_SKU": _safe(""),
                "ITEM_WARRANTY": _safe(str(row.get("warranty_days") or "")),
                "ITEM_PRICE": _safe(f"{price:.2f}"),
                "ITEM_DISCOUNT": _safe(f"{discount_amount:.2f}"),
                "ITEM_QUANTITY": _safe(str(qty)),
                "ITEM_SUM": _safe(f"{row_sum:.2f}"),
            })
        for idx, row in enumerate(order_parts or [], len(print_items) + 1):
            qty = int(row.get("quantity") or 1)
            price = float(row.get("price") or 0)
            discount_amount = _line_discount(
                price, qty, (row.get("discount_type") or "").strip().lower(),
                float(row.get("discount_value") or 0),
            )
            row_sum = round(price * qty - discount_amount, 2)
            total_items_sum += row_sum
            print_items.append({
                "INDEX": _safe(str(idx)),
                "ITEM_NAME": _safe(row.get("name") or row.get("part_name") or ""),
                "ITEM_SKU": _safe(row.get("part_number") or ""),
                "ITEM_WARRANTY": _safe(str(row.get("warranty_days") or "")),
                "ITEM_PRICE": _safe(f"{price:.2f}"),
                "ITEM_DISCOUNT": _safe(f"{discount_amount:.2f}"),
                "ITEM_QUANTITY": _safe(str(qty)),
                "ITEM_SUM": _safe(f"{row_sum:.2f}"),
            })
        values["TOTAL_ITEMS"] = _safe(f"{total_items_sum:.2f}")

        created_at_val = order_obj.get("created_at")
        formatted = ""
        if created_at_val:
            date_str = str(created_at_val).strip()
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    parsed = _dt.strptime(date_str[:19] if len(date_str) >= 19 else date_str, fmt)
                    formatted = parsed.strftime("%d.%m.%Y %H:%M:%S") if (" " in date_str or "T" in date_str) else parsed.strftime("%d.%m.%Y")
                    break
                except ValueError:
                    continue
            if not formatted and len(date_str) >= 10:
                try:
                    formatted = _dt.strptime(date_str[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
                except ValueError:
                    formatted = date_str
        values["CREATED_AT"] = _safe(formatted)

        values.update({
            "701809f9-23dc-4346-aff4-0aef32523aef": _safe(order_obj.get("device_type_name") or device_obj.get("device_type") or ""),
            "b6a8f943-e1b0-46e8-a321-b25fcfaf6976": _safe(order_obj.get("device_brand_name") or device_obj.get("device_brand") or ""),
            "c5286c7d-44aa-4579-8258-935b003998cf": _safe(order_obj.get("serial_number") or device_obj.get("serial_number") or ""),
            "c76b5bc7-7a68-4672-9542-cabaf2962600": _safe(order_obj.get("model") or ""),
            "bc1ae9b1-7b8b-4da6-add5-26982865629e": _safe(order_obj.get("appearance") or ""),
            "f93f4677-15b5-4e57-97e7-a345cb5b0e21": _safe(order_obj.get("symptom_tags") or ""),
            "dfd7aa33-fd89-462a-bbbc-39c1550415da": _safe(""),
        })
        try:
            values["PREPAYMENT"] = _safe(f"{float(order_obj.get('prepayment', 0) or 0):.2f}")
        except (ValueError, TypeError):
            values["PREPAYMENT"] = _safe("0.00")
        try:
            estimated_val = float(order_obj.get("estimated_cost", 0) or 0)
            values["ESTIMATED_COST"] = _safe(f"{estimated_val:.2f}") if estimated_val > 0 else ""
        except (ValueError, TypeError):
            values["ESTIMATED_COST"] = ""

        if amount_to_words:
            try:
                values["total.paid.words"] = _safe(amount_to_words(float(totals.get("paid", 0) or 0)))
                values["PREPAYMENT_WORDS"] = _safe(amount_to_words(float(order_obj.get("prepayment", 0) or 0)))
                est_for_words = float(order_obj.get("estimated_cost", 0) or 0)
                values["ESTIMATED_COST_WORDS"] = _safe(amount_to_words(est_for_words)) if est_for_words > 0 else ""
            except (ValueError, TypeError):
                values["total.paid.words"] = ""
                values["PREPAYMENT_WORDS"] = ""
                values["ESTIMATED_COST_WORDS"] = ""

        try:
            order_uuid = order_obj.get("order_id") or ""
            values["ticket.status.qrcode"] = _safe(
                url_for("orders.order_detail", order_id=order_uuid, _external=True) if order_uuid else ""
            )
        except Exception:
            values["ticket.status.qrcode"] = ""
        values["ticket.numberId.barcode"] = _safe(order_obj.get("order_id") or str(order_obj.get("id") or ""))

        if html_content and str(html_content).strip():
            result["customer"] = render_print_template(html_content, values, print_items)
        if sales_html and str(sales_html).strip():
            result["sales_receipt"] = render_print_template(sales_html, values, print_items)
        if work_html and str(work_html).strip():
            result["work_act"] = render_print_template(work_html, values, print_items)
    except Exception as exc:
        oid = getattr(order, "id", None) or (order_data.get("order") or {}).get("id")
        logger.error("Не удалось отрендерить шаблон печати клиента для заявки #%s: %s", oid, exc, exc_info=True)
    return result
