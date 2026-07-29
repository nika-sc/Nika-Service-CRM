"""
Маршруты раздела «Счета» (B2B: юрлица / ИП).
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.routes.main import permission_required
from app.services.action_log_service import ActionLogService
from app.services.inn_lookup_service import InnLookupService
from app.services.invoice_service import InvoiceService
from app.services.settings_service import SettingsService
from app.services.user_service import UserService
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.money_words import format_money_rub

bp = Blueprint("invoices", __name__, url_prefix="/invoices")
logger = logging.getLogger(__name__)

STATUS_LABELS = {
    "draft": "Черновик",
    "unpaid": "Не оплачен",
    "paid": "Оплачен",
    "cancelled": "Отменён",
}

ALLOWED_UPLOAD_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}


@bp.before_request
def _invoices_api_permission_gate():
    if not request.path.startswith("/invoices/api/") and not request.path.startswith("/api/inn/"):
        return None
    if not current_user.is_authenticated:
        return jsonify({"success": False, "error": "auth_required"}), 401
    if request.method in ("GET", "HEAD", "OPTIONS"):
        permission_name = "view_invoices"
    else:
        permission_name = "manage_invoices"
        if request.path.rstrip("/").endswith("/mark-paid") or request.path.endswith("/mark_paid"):
            permission_name = "mark_invoice_paid"
    if not UserService.check_permission(current_user.id, permission_name):
        # mark_paid also allowed for manage_invoices
        if permission_name == "mark_invoice_paid" and UserService.check_permission(
            current_user.id, "manage_invoices"
        ):
            return None
        return jsonify({
            "success": False,
            "error": "forbidden",
            "required_permission": permission_name,
        }), 403
    return None


def _status_badge(status: str) -> str:
    colors = {
        "draft": "secondary",
        "unpaid": "warning",
        "paid": "success",
        "cancelled": "dark",
    }
    return colors.get(status or "", "secondary")


@bp.route("/")
@login_required
@permission_required("view_invoices")
def index():
    status = (request.args.get("status") or "").strip() or None
    search = (request.args.get("q") or "").strip() or None
    page = request.args.get("page", 1, type=int)
    data = InvoiceService.list_invoices(status=status, search=search, page=page, per_page=50)
    for item in data["items"]:
        item["status_label"] = STATUS_LABELS.get(item.get("status"), item.get("status"))
        item["status_badge"] = _status_badge(item.get("status"))
        item["total_fmt"] = format_money_rub(int(item.get("total_cents") or 0))
    return render_template(
        "invoices/list.html",
        invoices=data["items"],
        pagination=data,
        status_filter=status or "",
        search=search or "",
        status_labels=STATUS_LABELS,
    )


@bp.route("/<int:invoice_id>")
@login_required
@permission_required("view_invoices")
def detail(invoice_id: int):
    try:
        inv = InvoiceService.get_invoice(invoice_id)
    except NotFoundError:
        flash("Счёт не найден", "danger")
        return redirect(url_for("invoices.index"))
    inv["status_label"] = STATUS_LABELS.get(inv.get("status"), inv.get("status"))
    inv["status_badge"] = _status_badge(inv.get("status"))
    inv["total_fmt"] = format_money_rub(int(inv.get("total_cents") or 0))
    for it in inv.get("items") or []:
        it["price_fmt"] = format_money_rub(int(it.get("price_cents") or 0))
        it["sum_fmt"] = format_money_rub(int(it.get("sum_cents") or 0))
    can_manage = UserService.check_permission(current_user.id, "manage_invoices")
    can_mark_paid = can_manage or UserService.check_permission(current_user.id, "mark_invoice_paid")
    return render_template(
        "invoices/detail.html",
        invoice=inv,
        can_manage=can_manage,
        can_mark_paid=can_mark_paid,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("manage_invoices")
def create_manual():
    if request.method == "GET":
        return render_template("invoices/create.html")
    data = request.get_json(silent=True) or request.form
    try:
        customer_id = int(data.get("customer_id") or 0)
        items = data.get("items")
        if isinstance(items, str):
            import json
            items = json.loads(items)
        invoice_id = InvoiceService.create_manual(
            customer_id=customer_id,
            items=items or [],
            due_date=(data.get("due_date") or None),
            comment=(data.get("comment") or None),
            user_id=current_user.id,
        )
        ActionLogService.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action_type="create",
            entity_type="invoice",
            entity_id=invoice_id,
            details={"source": "manual"},
        )
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "invoice_id": invoice_id,
                            "url": url_for("invoices.detail", invoice_id=invoice_id)})
        flash("Счёт создан", "success")
        return redirect(url_for("invoices.detail", invoice_id=invoice_id))
    except (ValidationError, NotFoundError, ValueError) as e:
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": str(e)}), 400
        flash(str(e), "danger")
        return redirect(url_for("invoices.create_manual"))


@bp.route("/settings", methods=["GET", "POST"])
@login_required
@permission_required("manage_invoices")
def settings_page():
    settings = SettingsService.get_general_settings()
    dadata_token = InnLookupService.get_api_token()
    templates = {
        "invoice_bill": SettingsService.get_print_template_fresh("invoice_bill"),
        "invoice_act": SettingsService.get_print_template_fresh("invoice_act"),
        "invoice_waybill": SettingsService.get_print_template_fresh("invoice_waybill"),
    }
    if request.method == "POST":
        form = request.form
        section = (form.get("settings_section") or "").strip()

        # Отдельное сохранение HTML-шаблона (как в Настройки → Формы для печати)
        if section == "print_template" or form.get("print_template_type"):
            ttype = (form.get("print_template_type") or "").strip()
            allowed = {"invoice_bill", "invoice_act", "invoice_waybill"}
            if ttype not in allowed:
                flash("Неизвестный тип шаблона печати", "error")
                return redirect(url_for("invoices.settings_page"))
            html = form.get("print_template_html") or ""
            # Поддержка старых имён полей на случай кэша/закладок
            if not html.strip():
                html = form.get(f"template_{ttype}") or ""
            if SettingsService.save_print_template(ttype, html):
                labels = {
                    "invoice_bill": "счёта",
                    "invoice_act": "акта",
                    "invoice_waybill": "накладной",
                }
                flash(f"Шаблон печати {labels.get(ttype, '')} сохранён", "success")
            else:
                flash("Не удалось сохранить шаблон печати", "error")
            return redirect(url_for("invoices.settings_page"))

        payload = dict(settings or {})
        payload.update({
            "logo_url": form.get("logo_url", settings.get("logo_url") or ""),
            "bank_name": form.get("bank_name", ""),
            "bik": form.get("bik", ""),
            "checking_account": form.get("checking_account", ""),
            "corr_account": form.get("corr_account", ""),
            "kpp": form.get("kpp", ""),
            "ogrnip": form.get("ogrnip", ""),
            "legal_address": form.get("legal_address", ""),
            "director_title": form.get("director_title", ""),
            "director_name": form.get("director_name", ""),
            "accountant_name": form.get("accountant_name", ""),
            "signature_url": form.get("signature_url", settings.get("signature_url") or ""),
            "stamp_url": form.get("stamp_url", settings.get("stamp_url") or ""),
            "logo_max_width": form.get("logo_max_width", settings.get("logo_max_width") or 220),
            "logo_max_height": form.get("logo_max_height", settings.get("logo_max_height") or 64),
            "signature_max_width": form.get("signature_max_width", settings.get("signature_max_width") or 160),
            "signature_max_height": form.get("signature_max_height", settings.get("signature_max_height") or 48),
            "stamp_max_width": form.get("stamp_max_width", settings.get("stamp_max_width") or 110),
            "stamp_max_height": form.get("stamp_max_height", settings.get("stamp_max_height") or 110),
        })
        SettingsService.save_general_settings(payload)
        if "dadata_api_token" in form:
            InnLookupService.save_api_token(form.get("dadata_api_token") or "")

        # Совместимость: старая единая форма с template_invoice_*
        for ttype in ("invoice_bill", "invoice_act", "invoice_waybill"):
            field = f"template_{ttype}"
            if field in form:
                html = form.get(field) or ""
                if html.strip():
                    SettingsService.save_print_template(ttype, html)

        flash("Настройки счетов сохранены", "success")
        return redirect(url_for("invoices.settings_page"))

    return render_template(
        "invoices/settings.html",
        settings=settings,
        dadata_token=dadata_token,
        templates=templates,
        dadata_configured=bool(dadata_token),
    )


@bp.route("/api/upload", methods=["POST"])
@login_required
@permission_required("manage_invoices")
def api_upload_asset():
    """Upload logo / signature / stamp into static/uploads/invoices."""
    file = request.files.get("file")
    kind = (request.form.get("kind") or "asset").strip()
    if not file or not file.filename:
        return jsonify({"success": False, "error": "Файл не выбран"}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXT:
        return jsonify({"success": False, "error": "Допустимы изображения: png, jpg, webp, gif, svg"}), 400
    upload_dir = os.path.join(current_app.static_folder, "uploads", "invoices")
    os.makedirs(upload_dir, exist_ok=True)
    safe = secure_filename(file.filename) or f"{kind}{ext}"
    name = f"{kind}_{uuid.uuid4().hex[:10]}_{safe}"
    path = os.path.join(upload_dir, name)
    file.save(path)
    url = url_for("static", filename=f"uploads/invoices/{name}")
    return jsonify({"success": True, "url": url})


@bp.route("/<int:invoice_id>/print/<doc_type>")
@login_required
@permission_required("view_invoices")
def print_document(invoice_id: int, doc_type: str):
    # ?blank_signs=1 — бланк без картинок подписи/печати (для живого проставления)
    blank_raw = (request.args.get("blank_signs") or request.args.get("wet") or "").strip().lower()
    blank_signs = blank_raw in ("1", "true", "yes", "on")
    try:
        html = InvoiceService.render_document(invoice_id, doc_type, blank_signs=blank_signs)
    except (ValidationError, NotFoundError) as e:
        flash(str(e), "danger")
        return redirect(url_for("invoices.detail", invoice_id=invoice_id))
    from app.utils.print_template_renderer import strip_page_at_rules
    from app.services.settings_service import SettingsService

    settings = SettingsService.get_general_settings() or {}
    html = strip_page_at_rules(html)
    return render_template(
        "invoices/print.html",
        content=html,
        doc_type=doc_type,
        invoice_id=invoice_id,
        blank_signs=blank_signs,
        print_page_size=settings.get("print_page_size") or "A4",
        print_margin_mm=settings.get("print_margin_mm") if settings.get("print_margin_mm") is not None else 3,
        logo_max_width=settings.get("logo_max_width") or 220,
        logo_max_height=settings.get("logo_max_height") or 64,
        signature_max_width=settings.get("signature_max_width") or 160,
        signature_max_height=settings.get("signature_max_height") or 48,
        stamp_max_width=settings.get("stamp_max_width") or 110,
        stamp_max_height=settings.get("stamp_max_height") or 110,
    )


@bp.route("/api/list")
@login_required
@permission_required("view_invoices")
def api_list():
    data = InvoiceService.list_invoices(
        status=request.args.get("status") or None,
        search=request.args.get("q") or None,
        order_id=request.args.get("order_id", type=int),
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 50, type=int),
    )
    return jsonify({"success": True, **data})


@bp.route("/api/<int:invoice_id>")
@login_required
@permission_required("view_invoices")
def api_get(invoice_id: int):
    try:
        inv = InvoiceService.get_invoice(invoice_id)
        return jsonify({"success": True, "invoice": inv})
    except NotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404


@bp.route("/api/<int:invoice_id>/mark-paid", methods=["POST"])
@login_required
def api_mark_paid(invoice_id: int):
    if not (
        UserService.check_permission(current_user.id, "mark_invoice_paid")
        or UserService.check_permission(current_user.id, "manage_invoices")
    ):
        return jsonify({"success": False, "error": "forbidden"}), 403
    try:
        inv = InvoiceService.mark_paid(
            invoice_id, user_id=current_user.id, username=current_user.username
        )
        ActionLogService.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action_type="update",
            entity_type="invoice",
            entity_id=invoice_id,
            details={
                "status": "paid",
                "payment_id": inv.get("payment_id"),
                "shop_sale_id": inv.get("shop_sale_id"),
                "order_id": inv.get("order_id"),
            },
        )
        warning = None
        if inv.get("shop_sale_id") and not inv.get("order_id"):
            warning = (
                f"Счёт проведён без заявки и ушёл в магазин: продажа #{inv.get('shop_sale_id')}. "
                "Касса и списание склада — как у продажи в магазине (не как оплата по заявке)."
            )
        elif inv.get("order_id") and inv.get("payment_id"):
            warning = (
                f"Оплата проведена по заявке #{inv.get('order_id')} "
                f"(payment #{inv.get('payment_id')})."
            )
        return jsonify({"success": True, "invoice": inv, "warning": warning})
    except (ValidationError, NotFoundError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


@bp.route("/api/<int:invoice_id>/cancel", methods=["POST"])
@login_required
@permission_required("manage_invoices")
def api_cancel(invoice_id: int):
    try:
        inv = InvoiceService.cancel(invoice_id)
        ActionLogService.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action_type="update",
            entity_type="invoice",
            entity_id=invoice_id,
            details={"status": "cancelled"},
        )
        return jsonify({"success": True, "invoice": inv})
    except (ValidationError, NotFoundError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


@bp.route("/api/from-order/<int:order_id>", methods=["POST"])
@login_required
@permission_required("manage_invoices")
def api_from_order(order_id: int):
    data = request.get_json(silent=True) or {}
    try:
        invoice_id = InvoiceService.create_from_order(
            order_id,
            user_id=current_user.id,
            service_ids=data.get("service_ids"),
            part_ids=data.get("part_ids"),
            due_date=data.get("due_date"),
            comment=data.get("comment"),
        )
        ActionLogService.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action_type="create",
            entity_type="invoice",
            entity_id=invoice_id,
            details={"source": "order", "order_id": order_id},
        )
        return jsonify({
            "success": True,
            "invoice_id": invoice_id,
            "url": url_for("invoices.detail", invoice_id=invoice_id),
        })
    except (ValidationError, NotFoundError) as e:
        return jsonify({"success": False, "error": str(e)}), 400


# INN lookup lives under /api/inn/lookup — registered on same blueprint without prefix conflict
inn_bp = Blueprint("inn_lookup", __name__)


@inn_bp.route("/api/inn/lookup", methods=["POST"])
@login_required
def api_inn_lookup():
    if not (
        UserService.check_permission(current_user.id, "manage_invoices")
        or UserService.check_permission(current_user.id, "edit_customers")
        or UserService.check_permission(current_user.id, "manage_customers")
        or UserService.check_permission(current_user.id, "create_customers")
        or UserService.check_permission(current_user.id, "view_customers")
    ):
        # Soft: allow any authenticated staff that can edit clients; fallback manage_invoices
        if not UserService.check_permission(current_user.id, "view_orders"):
            return jsonify({"success": False, "error": "forbidden"}), 403
    data = request.get_json(silent=True) or {}
    try:
        result = InnLookupService.lookup(data.get("inn") or "")
        return jsonify({"success": True, **result})
    except ValidationError as e:
        msg = str(e)
        code = 503 if "не настроено" in msg.lower() or "токен" in msg.lower() else 400
        return jsonify({"success": False, "error": msg}), code
