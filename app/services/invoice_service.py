"""Сервис счетов для юрлиц и ИП."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.database.queries.invoice_queries import InvoiceQueries
from app.database.queries.order_queries import OrderQueries
from app.services.settings_service import SettingsService
from app.services.customer_service import CustomerService
from app.utils.exceptions import ValidationError, NotFoundError
from app.utils.money_words import cents_to_words_rub, format_money_rub
from app.utils.print_template_renderer import render_print_template
from app.utils.datetime_utils import get_moscow_now_naive

logger = logging.getLogger(__name__)


def _to_cents(value) -> int:
    try:
        return int(round(float(value) * 100))
    except (TypeError, ValueError):
        return 0


def _seller_snapshot_from_settings(settings: Dict) -> Dict:
    return {
        "org_name": settings.get("org_name") or "",
        "inn": settings.get("inn") or "",
        "kpp": settings.get("kpp") or "",
        "ogrn": settings.get("ogrn") or "",
        "ogrnip": settings.get("ogrnip") or "",
        "phone": settings.get("phone") or "",
        "address": settings.get("legal_address") or settings.get("address") or "",
        "bank_name": settings.get("bank_name") or "",
        "bik": settings.get("bik") or "",
        "checking_account": settings.get("checking_account") or "",
        "corr_account": settings.get("corr_account") or "",
        "director_title": settings.get("director_title") or "Руководитель",
        "director_name": settings.get("director_name") or settings.get("signature_name") or "",
        "accountant_name": settings.get("accountant_name") or "",
        "logo_url": settings.get("logo_url") or "",
        "signature_url": settings.get("signature_url") or "",
        "stamp_url": settings.get("stamp_url") or "",
    }


def _buyer_from_customer(customer: Dict) -> Dict:
    kind = (customer.get("customer_kind") or "person").strip() or "person"
    name = (customer.get("legal_name") or customer.get("name") or "").strip()
    return {
        "buyer_kind": kind,
        "buyer_name": name,
        "buyer_inn": customer.get("inn") or "",
        "buyer_kpp": customer.get("kpp") or "",
        "buyer_ogrn": customer.get("ogrn") or "",
        "buyer_address": customer.get("legal_address") or "",
        "buyer_bank_name": customer.get("bank_name") or "",
        "buyer_bik": customer.get("bik") or "",
        "buyer_checking_account": customer.get("checking_account") or "",
        "buyer_corr_account": customer.get("corr_account") or "",
    }


def _format_party(name, inn=None, kpp=None, address=None, ogrn=None) -> str:
    parts = [name or ""]
    if inn:
        parts.append(f"ИНН {inn}")
    if kpp:
        parts.append(f"КПП {kpp}")
    if ogrn:
        parts.append(f"ОГРН {ogrn}")
    if address:
        parts.append(address)
    return ", ".join(p for p in parts if p)


def _print_asset_url(*candidates) -> str:
    """URL логотипа/подписи/печати: валидный путь/http, иначе следующий кандидат."""
    for raw in candidates:
        url = (raw or "").strip()
        if not url:
            continue
        # отсекаем мусор вроде "admin" из старых снимков
        if url.startswith("/") or url.startswith("http://") or url.startswith("https://"):
            return url
    return ""


def _customer_as_dict(customer) -> Dict:
    if isinstance(customer, dict):
        return customer
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": getattr(customer, "phone", None),
        "email": getattr(customer, "email", None),
        "customer_kind": getattr(customer, "customer_kind", None) or "person",
        "inn": getattr(customer, "inn", None),
        "kpp": getattr(customer, "kpp", None),
        "ogrn": getattr(customer, "ogrn", None),
        "legal_name": getattr(customer, "legal_name", None),
        "legal_address": getattr(customer, "legal_address", None),
        "bank_name": getattr(customer, "bank_name", None),
        "bik": getattr(customer, "bik", None),
        "checking_account": getattr(customer, "checking_account", None),
        "corr_account": getattr(customer, "corr_account", None),
    }


class InvoiceService:
    @staticmethod
    def list_invoices(**kwargs) -> Dict:
        return InvoiceQueries.list_invoices(**kwargs)

    @staticmethod
    def get_invoice(invoice_id: int) -> Dict:
        inv = InvoiceQueries.get_invoice(invoice_id)
        if not inv:
            raise NotFoundError("Счёт не найден")
        return inv

    @staticmethod
    def create_from_order(
        order_id: int,
        *,
        user_id: Optional[int] = None,
        service_ids: Optional[List[int]] = None,
        part_ids: Optional[List[int]] = None,
        due_date: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> int:
        from app.services.order_service import OrderService

        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError("Заявка не найдена")

        if hasattr(order, "to_dict"):
            order_data = order.to_dict()
        elif isinstance(order, dict):
            order_data = order
        else:
            order_data = {
                "id": getattr(order, "id", None),
                "customer_id": getattr(order, "customer_id", None) or getattr(order, "client_id", None),
                "client_id": getattr(order, "client_id", None),
            }

        customer_id = order_data.get("customer_id") or order_data.get("client_id")
        if not customer_id:
            raise ValidationError("У заявки нет клиента")

        customer = _customer_as_dict(CustomerService.get_customer(int(customer_id)))
        kind = (customer.get("customer_kind") or "person").strip()
        inn = (customer.get("inn") or "").strip()
        if kind not in ("ip", "legal") or not inn:
            raise ValidationError(
                "Для выставления счёта укажите в карточке клиента тип ИП или Юрлицо и ИНН "
                "(Клиенты → Редактировать → блок «Реквизиты»)"
            )

        services = OrderQueries.get_order_services(order_id)
        parts = OrderQueries.get_order_parts(order_id)
        selected_services = set(service_ids) if service_ids is not None else None
        selected_parts = set(part_ids) if part_ids is not None else None
        items: List[Dict] = []

        for s in services:
            sid = int(s.get("id"))
            if selected_services is not None and sid not in selected_services:
                continue
            qty = float(s.get("quantity") or 1)
            price = float(s.get("price") or s.get("service_price") or 0)
            title = (s.get("name") or s.get("service_name") or "Услуга").strip()
            price_cents = _to_cents(price)
            items.append({
                "line_type": "service",
                "title": title,
                "qty": qty,
                "unit": "шт",
                "price_cents": price_cents,
                "sum_cents": int(round(qty * price_cents)),
                "source_order_service_id": sid,
            })

        for p in parts:
            pid = int(p.get("id"))
            if selected_parts is not None and pid not in selected_parts:
                continue
            qty = float(p.get("quantity") or 1)
            price = float(p.get("price") or p.get("sale_price") or 0)
            title = (p.get("name") or p.get("part_name") or "Товар").strip()
            price_cents = _to_cents(price)
            items.append({
                "line_type": "part",
                "title": title,
                "qty": qty,
                "unit": p.get("unit") or "шт",
                "price_cents": price_cents,
                "sum_cents": int(round(qty * price_cents)),
                "source_order_part_id": pid,
            })

        if not items:
            raise ValidationError("Нет позиций для счёта (услуги/товары)")

        return InvoiceService._create_invoice_record(
            customer=customer,
            order_id=order_id,
            items=items,
            due_date=due_date,
            comment=comment,
            user_id=user_id,
        )

    @staticmethod
    def create_manual(
        *,
        customer_id: int,
        items: List[Dict],
        due_date: Optional[str] = None,
        comment: Optional[str] = None,
        user_id: Optional[int] = None,
        order_id: Optional[int] = None,
    ) -> int:
        customer = _customer_as_dict(CustomerService.get_customer(int(customer_id)))
        kind = (customer.get("customer_kind") or "person").strip()
        inn = (customer.get("inn") or "").strip()
        if kind not in ("ip", "legal") or not inn:
            raise ValidationError(
                "Выберите клиента типа ИП/Юрлицо с ИНН (карточка клиента → Реквизиты)"
            )
        prepared = []
        for it in items or []:
            qty = float(it.get("qty") or 1)
            price_cents = int(it.get("price_cents") or _to_cents(it.get("price") or 0))
            prepared.append({
                "line_type": it.get("line_type") or "service",
                "title": (it.get("title") or "").strip() or "Позиция",
                "qty": qty,
                "unit": it.get("unit") or "шт",
                "price_cents": price_cents,
                "sum_cents": int(it.get("sum_cents") or round(qty * price_cents)),
                "vat_label": it.get("vat_label") or "Без НДС",
                "catalog_part_id": it.get("catalog_part_id") or it.get("part_id"),
                "catalog_service_id": it.get("catalog_service_id") or it.get("service_id"),
            })
        if not prepared:
            raise ValidationError("Добавьте хотя бы одну позицию")
        return InvoiceService._create_invoice_record(
            customer=customer,
            order_id=order_id,
            items=prepared,
            due_date=due_date,
            comment=comment,
            user_id=user_id,
        )

    @staticmethod
    def _create_invoice_record(*, customer, items, order_id, due_date, comment, user_id) -> int:
        settings = SettingsService.get_general_settings()
        seller = _seller_snapshot_from_settings(settings)
        buyer = _buyer_from_customer(customer)
        total = sum(int(i.get("sum_cents") or 0) for i in items)
        year = get_moscow_now_naive().year
        number = InvoiceQueries.next_number("invoice", year)
        has_services = any(i.get("line_type") == "service" for i in items)
        has_parts = any(i.get("line_type") == "part" for i in items)
        act_number = InvoiceQueries.next_number("act", year) if has_services else None
        waybill_number = InvoiceQueries.next_number("waybill", year) if has_parts else None
        data = {
            "number": number,
            "act_number": act_number,
            "waybill_number": waybill_number,
            "due_date": due_date,
            "status": "unpaid",
            "order_id": order_id,
            "customer_id": int(customer["id"]),
            **buyer,
            "seller_snapshot": seller,
            "subtotal_cents": total,
            "vat_mode": "none",
            "total_cents": total,
            "comment": comment,
            "created_by": user_id,
        }
        return InvoiceQueries.create_invoice(data, items)

    @staticmethod
    def mark_paid(invoice_id: int, user_id: Optional[int] = None, username: Optional[str] = None) -> Dict:
        inv = InvoiceService.get_invoice(invoice_id)
        if inv["status"] == "cancelled":
            raise ValidationError("Нельзя оплатить отменённый счёт")
        if inv["status"] == "paid" and (inv.get("payment_id") or inv.get("shop_sale_id")):
            return inv
        if inv["status"] not in ("unpaid", "draft", "paid"):
            raise ValidationError("Недопустимый статус счёта для оплаты")
        # status==paid без проводки (старые счета без заявки) — допроводим склад/кассу ниже

        payment_id = inv.get("payment_id")
        shop_sale_id = inv.get("shop_sale_id")
        order_id = inv.get("order_id")
        amount_rub = (inv.get("total_cents") or 0) / 100.0
        if amount_rub <= 0:
            raise ValidationError("Сумма счёта должна быть больше нуля")

        if order_id and not payment_id:
            from app.services.payment_service import PaymentService
            payment_id = PaymentService.add_payment(
                order_id=int(order_id),
                amount=amount_rub,
                payment_type="transfer",
                user_id=user_id,
                username=username,
                comment=f"Оплата по счёту №{inv.get('number')}",
                kind="payment",
                status="captured",
                idempotency_key=f"invoice-paid-{invoice_id}",
                invoice_id=invoice_id,
            )
        elif not order_id and not shop_sale_id:
            # Счёт без заявки: продажа магазина (касса + списание склада по catalog_part_id)
            shop_sale_id = InvoiceService._create_shop_sale_for_invoice(
                inv, user_id=user_id, username=username
            )

        now = get_moscow_now_naive().isoformat(sep=" ", timespec="seconds")
        InvoiceQueries.update_status(
            invoice_id,
            "paid",
            paid_at=now,
            paid_by_user_id=user_id,
            payment_id=payment_id,
            shop_sale_id=shop_sale_id,
        )
        return InvoiceService.get_invoice(invoice_id)

    @staticmethod
    def _resolve_catalog_ids(inv: Dict) -> List[Dict]:
        """Подставляет catalog_* из БД; для товаров без id — попытка найти по точному названию."""
        from app.database.connection import get_db_connection
        import sqlite3

        items = list(inv.get("items") or [])
        resolved = []
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cur = conn.cursor()
            for it in items:
                row = dict(it)
                line_type = (row.get("line_type") or "service").strip()
                if line_type == "part" and not row.get("catalog_part_id"):
                    title = (row.get("title") or "").strip()
                    if title:
                        cur.execute(
                            """
                            SELECT id FROM parts
                            WHERE COALESCE(is_deleted, 0) = 0
                              AND (name = ? OR name LIKE ?)
                            ORDER BY CASE WHEN name = ? THEN 0 ELSE 1 END, id
                            LIMIT 1
                            """,
                            (title, f"%{title}%", title),
                        )
                        found = cur.fetchone()
                        if found:
                            row["catalog_part_id"] = int(found["id"])
                            InvoiceQueries.set_item_catalog_ids(
                                int(row["id"]), catalog_part_id=int(found["id"])
                            )
                if line_type != "part" and not row.get("catalog_service_id"):
                    title = (row.get("title") or "").strip()
                    if title:
                        cur.execute(
                            """
                            SELECT id FROM services
                            WHERE name = ? OR name LIKE ?
                            ORDER BY CASE WHEN name = ? THEN 0 ELSE 1 END, id
                            LIMIT 1
                            """,
                            (title, f"%{title}%", title),
                        )
                        found = cur.fetchone()
                        if found:
                            row["catalog_service_id"] = int(found["id"])
                            InvoiceQueries.set_item_catalog_ids(
                                int(row["id"]), catalog_service_id=int(found["id"])
                            )
                resolved.append(row)
        return resolved

    @staticmethod
    def _create_shop_sale_for_invoice(
        inv: Dict, *, user_id: Optional[int], username: Optional[str]
    ) -> int:
        from app.services.finance_service import FinanceService

        items = InvoiceService._resolve_catalog_ids(inv)
        shop_items: List[Dict] = []
        missing_parts = []
        for it in items:
            qty = float(it.get("qty") or 1)
            price = (int(it.get("price_cents") or 0)) / 100.0
            line_type = (it.get("line_type") or "service").strip()
            title = (it.get("title") or "Позиция").strip()
            if line_type == "part":
                part_id = it.get("catalog_part_id")
                if not part_id:
                    missing_parts.append(title)
                    continue
                shop_items.append({
                    "type": "part",
                    "part_id": int(part_id),
                    "quantity": qty,
                    "price": price,
                    "name": title,
                })
            else:
                shop_items.append({
                    "type": "service",
                    "service_id": int(it["catalog_service_id"]) if it.get("catalog_service_id") else None,
                    "quantity": qty,
                    "price": price,
                    "name": title,
                })

        if missing_parts:
            raise ValidationError(
                "Нельзя провести оплату: товар(ы) не привязаны к складу — "
                + "; ".join(missing_parts[:3])
                + ". Выберите позицию из каталога при создании счёта "
                "(или выставьте счёт из заявки)."
            )
        if not shop_items:
            raise ValidationError("Нет позиций для проводки продажи")

        sale_id, _meta = FinanceService.create_shop_sale(
            items=shop_items,
            customer_id=inv.get("customer_id"),
            customer_name=inv.get("buyer_name") or inv.get("customer_name"),
            payment_method="transfer",
            comment=f"Оплата по счёту №{inv.get('number')}",
            created_by_id=user_id,
            created_by_username=username,
        )
        return int(sale_id)

    @staticmethod
    def cancel(invoice_id: int) -> Dict:
        inv = InvoiceService.get_invoice(invoice_id)
        if inv["status"] == "paid" and inv.get("payment_id"):
            raise ValidationError(
                "Счёт уже оплачен. Сначала отмените связанную оплату в заявке, затем отмените счёт."
            )
        InvoiceQueries.update_status(invoice_id, "cancelled")
        return InvoiceService.get_invoice(invoice_id)

    @staticmethod
    def render_document(invoice_id: int, doc_type: str) -> str:
        inv = InvoiceService.get_invoice(invoice_id)
        mapping = {
            "bill": ("invoice_bill", inv.get("number")),
            "act": ("invoice_act", inv.get("act_number") or inv.get("number")),
            "waybill": ("invoice_waybill", inv.get("waybill_number") or inv.get("number")),
        }
        if doc_type not in mapping:
            raise ValidationError("Неизвестный тип документа")
        template_type, doc_number = mapping[doc_type]
        tpl = SettingsService.get_print_template_fresh(template_type) or SettingsService.get_print_template(template_type)
        if not tpl or not tpl.get("html_content"):
            raise NotFoundError("Шаблон печати не найден")

        seller = inv.get("seller") or {}
        items_src = list(inv.get("items") or [])
        if doc_type == "act":
            filtered = [i for i in items_src if i.get("line_type") == "service"]
            items_src = filtered or items_src
        elif doc_type == "waybill":
            items_src = [i for i in items_src if i.get("line_type") == "part"]

        total_cents = int(inv.get("total_cents") or 0) if doc_type == "bill" else sum(int(i.get("sum_cents") or 0) for i in items_src)
        issued = inv.get("issued_at") or ""
        if isinstance(issued, datetime):
            doc_date = issued.strftime("%d.%m.%Y")
        else:
            try:
                doc_date = datetime.fromisoformat(str(issued).replace("Z", "")).strftime("%d.%m.%Y")
            except Exception:
                doc_date = str(issued)[:10]

        gs = SettingsService.get_general_settings() or {}
        # Снимок счёта может быть без/с битым URL — берём актуальные из настроек
        logo = _print_asset_url(seller.get("logo_url"), gs.get("logo_url"))
        sig = _print_asset_url(seller.get("signature_url"), gs.get("signature_url"))
        stamp = _print_asset_url(seller.get("stamp_url"), gs.get("stamp_url"))
        logo_mw = int(gs.get("logo_max_width") or 220)
        logo_mh = int(gs.get("logo_max_height") or 64)
        sig_mw = int(gs.get("signature_max_width") or 160)
        sig_mh = int(gs.get("signature_max_height") or 48)
        stamp_mw = int(gs.get("stamp_max_width") or 110)
        stamp_mh = int(gs.get("stamp_max_height") or 110)
        logo_html = (
            f'<img class="logo" src="{logo}" alt="logo" '
            f'style="max-width:{logo_mw}px;max-height:{logo_mh}px;width:auto;height:auto;">'
            if logo else ""
        )
        sig_html = (
            f'<img class="sig" src="{sig}" alt="подпись" '
            f'style="max-width:{sig_mw}px;max-height:{sig_mh}px;width:auto;height:auto;">'
            if sig else ""
        )
        stamp_html = (
            f'<img class="stamp" src="{stamp}" alt="печать" '
            f'style="max-width:{stamp_mw}px;max-height:{stamp_mh}px;width:auto;height:auto;opacity:.9;">'
            if stamp else ""
        )
        due = inv.get("due_date")
        due_html = f'<div class="due">Оплату необходимо произвести до <b>{due}</b></div>' if due else ""
        comment = (inv.get("comment") or "").strip()
        if doc_type == "bill":
            basis = comment
        else:
            basis = f"Счёт №{inv.get('number')}" if inv.get("number") else comment
        basis_html = f'<div class="basis">{basis}</div>' if basis else ""

        seller_full = _format_party(seller.get("org_name"), seller.get("inn"), seller.get("kpp"), seller.get("address"), seller.get("ogrn") or seller.get("ogrnip"))
        buyer_full = _format_party(inv.get("buyer_name"), inv.get("buyer_inn"), inv.get("buyer_kpp"), inv.get("buyer_address"), inv.get("buyer_ogrn"))
        values = {
            "DOC_NUMBER": str(doc_number or inv.get("number") or ""),
            "DOC_DATE": doc_date,
            "SELLER_NAME": seller.get("org_name") or "",
            "SELLER_INN": seller.get("inn") or "",
            "SELLER_KPP": seller.get("kpp") or "",
            "SELLER_BANK_NAME": seller.get("bank_name") or "",
            "SELLER_BIK": seller.get("bik") or "",
            "SELLER_CHECKING_ACCOUNT": seller.get("checking_account") or "",
            "SELLER_CORR_ACCOUNT": seller.get("corr_account") or "",
            "SELLER_FULL": seller_full,
            "SELLER_DIRECTOR": seller.get("director_name") or "",
            "SELLER_ACCOUNTANT": seller.get("accountant_name") or "",
            "BUYER_FULL": buyer_full,
            "TOTAL": format_money_rub(total_cents),
            "TOTAL_WORDS": cents_to_words_rub(total_cents),
            "ITEMS_COUNT": str(len(items_src)),
            "LOGO_HTML": logo_html,
            "SIGNATURE_HTML": sig_html,
            "STAMP_HTML": stamp_html,
            "DUE_HTML": due_html,
            "BASIS": basis,
            "BASIS_HTML": basis_html,
            "COMMENT": comment,
        }
        print_items = []
        for i, it in enumerate(items_src, start=1):
            qty = it.get("qty") or 1
            qty_s = str(qty)
            if isinstance(qty, float):
                qty_s = (f"{qty:.3f}").rstrip("0").rstrip(".")
            print_items.append({
                "N": str(i),
                "TITLE": it.get("title") or "",
                "QTY": qty_s,
                "UNIT": it.get("unit") or "шт",
                "VAT": it.get("vat_label") or "Без НДС",
                "PRICE": format_money_rub(int(it.get("price_cents") or 0)),
                "SUM": format_money_rub(int(it.get("sum_cents") or 0)),
            })
        return render_print_template(tpl["html_content"], values, print_items)
