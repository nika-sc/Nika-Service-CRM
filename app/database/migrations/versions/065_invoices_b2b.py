"""
Миграция 065: счета для юрлиц/ИП (B2B).

- Реквизиты продавца в general_settings (банк, КПП, подпись/печать)
- Юр.поля customers
- invoices / invoice_items / invoice_sequences
- payments.invoice_id
- print_templates: invoice_bill, invoice_act, invoice_waybill
- permissions: view_invoices, manage_invoices, mark_invoice_paid
"""
from __future__ import annotations

import logging
import sqlite3

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def _table_columns(cursor, table: str) -> set:
    cursor.execute(f"PRAGMA table_info({table})")
    return {r[1] for r in cursor.fetchall()}


def _add_column_if_missing(cursor, table: str, column: str, ddl: str) -> None:
    cols = _table_columns(cursor, table)
    if column not in cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


DEFAULT_INVOICE_BILL = """<style>
.bill { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #000; line-height: 1.35; }
.bill table { border-collapse: collapse; width: 100%; }
.bill .due { margin: 0 0 6px; }
.bill .basis { margin: 0 0 10px; }
.bill .bank td { border: 1px solid #000; padding: 3px 6px; vertical-align: top; }
.bill .bank .lbl { font-size: 10px; color: #333; }
.bill .bank .val { font-size: 12px; }
.bill h1 { font-size: 15px; font-weight: 700; margin: 14px 0 10px; border-bottom: 2px solid #000; padding-bottom: 4px; }
.bill .party { margin: 6px 0; }
.bill .party b { display: inline-block; min-width: 95px; }
.bill .items { margin-top: 10px; }
.bill .items th, .bill .items td { border: 1px solid #000; padding: 3px 5px; }
.bill .items th { background: #f0f0f0; font-weight: 700; text-align: center; }
.bill .c { text-align: center; }
.bill .r { text-align: right; }
.bill .totals { margin-top: 8px; width: 100%; }
.bill .totals td { padding: 2px 0; border: none; }
.bill .words { margin: 8px 0 18px; }
.bill .sign { margin-top: 28px; width: 100%; }
.bill .sign td { border: none; vertical-align: bottom; padding: 0; width: 50%; }
.bill .sign .line { display: inline-block; min-width: 160px; border-bottom: 1px solid #000; margin: 0 6px; height: 18px; }
.bill .sign .name { margin-top: 4px; padding-left: 110px; }
.bill .sign .box { position: relative; min-height: 64px; }
.bill .sign img.sig { max-height: 48px; position: absolute; left: 110px; top: -6px; }
.bill .sign img.stamp { max-height: 95px; position: absolute; left: 170px; top: -20px; opacity: .85; }
.bill .logo { max-height: 56px; margin-bottom: 8px; }
</style>
<div class="bill">
##LOGO_HTML##
##DUE_HTML##
##BASIS_HTML##

<table class="bank">
<tr>
<td colspan="2" rowspan="2" width="50%"><div class="lbl">Банк получателя</div><div class="val"><b>##SELLER_BANK_NAME##</b></div></td>
<td width="12%"><div class="lbl">БИК</div></td>
<td width="38%"><div class="val">##SELLER_BIK##</div></td>
</tr>
<tr>
<td><div class="lbl">Сч. №</div></td>
<td><div class="val">##SELLER_CORR_ACCOUNT##</div></td>
</tr>
<tr>
<td width="25%"><div class="lbl">ИНН</div><div class="val">##SELLER_INN##</div></td>
<td width="25%"><div class="lbl">КПП</div><div class="val">##SELLER_KPP##</div></td>
<td colspan="2"><div class="lbl">Получатель</div><div class="val"><b>##SELLER_NAME##</b><br>Сч. № ##SELLER_CHECKING_ACCOUNT##</div></td>
</tr>
</table>

<h1>Счет на оплату № ##DOC_NUMBER## от ##DOC_DATE##</h1>

<div class="party"><b>Поставщик:</b> ##SELLER_FULL##</div>
<div class="party"><b>Покупатель:</b> ##BUYER_FULL##</div>

<table class="items">
<thead>
<tr>
<th width="28">№</th>
<th>Товары (работы, услуги)</th>
<th width="55">Кол-во</th>
<th width="55">Ед.</th>
<th width="70">НДС</th>
<th width="85">Цена</th>
<th width="90">Сумма</th>
</tr>
</thead>
<tbody>
<tr data-for="ITEMS">
<td class="c">##N##</td>
<td>##TITLE##</td>
<td class="r">##QTY##</td>
<td class="c">##UNIT##</td>
<td class="c">##VAT##</td>
<td class="r">##PRICE##</td>
<td class="r">##SUM##</td>
</tr>
</tbody>
</table>

<table class="totals">
<tr>
<td>Всего наименований ##ITEMS_COUNT## на сумму ##TOTAL##</td>
<td class="r"><b>Итого к оплате: ##TOTAL##</b></td>
</tr>
</table>
<div class="words"><b>##TOTAL_WORDS##</b></div>

<table class="sign">
<tr>
<td>
<div class="box">Руководитель<span class="line"></span>##SIGNATURE_HTML####STAMP_HTML##
<div class="name">##SELLER_DIRECTOR##</div></div>
</td>
<td>
<div class="box">Бухгалтер<span class="line"></span>
<div class="name">##SELLER_ACCOUNTANT##</div></div>
</td>
</tr>
</table>
</div>
"""

DEFAULT_INVOICE_ACT = """<style>
.act { font-family: Arial, Helvetica, sans-serif; font-size: 12px; color: #000; line-height: 1.35; }
.act table { border-collapse: collapse; width: 100%; }
.act h1 { font-size: 15px; font-weight: 700; margin: 0 0 12px; border-bottom: 2px solid #000; padding-bottom: 4px; }
.act .party { margin: 8px 0; }
.act .party b { display: inline-block; min-width: 95px; }
.act .items { margin: 12px 0; }
.act .items th, .act .items td { border: 1px solid #000; padding: 3px 5px; }
.act .items th { background: #f0f0f0; font-weight: 700; text-align: center; }
.act .c { text-align: center; }
.act .r { text-align: right; }
.act .total-line { margin: 10px 0 4px; text-align: right; font-weight: 700; }
.act .services-sum { margin: 0 0 4px; }
.act .words { margin: 4px 0 12px; font-weight: 700; }
.act .disclaimer { margin: 12px 0 24px; text-align: justify; }
.act .sign { margin-top: 20px; width: 100%; }
.act .sign td { border: none; vertical-align: bottom; padding: 0; width: 50%; }
.act .sign .line { display: inline-block; min-width: 180px; border-bottom: 1px solid #000; margin: 0 6px; height: 18px; }
.act .sign .name { margin-top: 4px; padding-left: 100px; }
.act .sign .box { position: relative; min-height: 64px; }
.act .sign img.sig { max-height: 48px; position: absolute; left: 100px; top: -6px; }
.act .sign img.stamp { max-height: 95px; position: absolute; left: 160px; top: -20px; opacity: .85; }
.act .logo { max-height: 56px; margin-bottom: 8px; }
</style>
<div class="act">
##LOGO_HTML##

<h1>Акт № ##DOC_NUMBER## от ##DOC_DATE##</h1>

<table class="items">
<thead>
<tr>
<th width="28">№</th>
<th>Услуга</th>
<th width="55">Кол-во</th>
<th width="55">Ед.</th>
<th width="70">НДС</th>
<th width="85">Цена</th>
<th width="90">Сумма</th>
</tr>
</thead>
<tbody>
<tr data-for="ITEMS">
<td class="c">##N##</td>
<td>##TITLE##</td>
<td class="r">##QTY##</td>
<td class="c">##UNIT##</td>
<td class="c">##VAT##</td>
<td class="r">##PRICE##</td>
<td class="r">##SUM##</td>
</tr>
</tbody>
</table>

<div class="party"><b>Исполнитель:</b> ##SELLER_FULL##</div>
<div class="party"><b>Заказчик:</b> ##BUYER_FULL##</div>

<div class="total-line">Итого к оплате: ##TOTAL##</div>
<div class="services-sum">Всего оказано услуг на сумму ##TOTAL## руб.</div>
<div class="words">##TOTAL_WORDS##</div>

<p class="disclaimer">Вышеперечисленные услуги оказаны в полном объеме и в установленный срок. Заказчик не имеет претензий по качеству, срокам и объемам оказанных услуг.</p>

<table class="sign">
<tr>
<td>
<div class="box">Заказчик<span class="line"></span></div>
</td>
<td>
<div class="box">Исполнитель<span class="line"></span>##SIGNATURE_HTML####STAMP_HTML##
<div class="name">##SELLER_DIRECTOR##</div></div>
</td>
</tr>
</table>
</div>
"""

DEFAULT_INVOICE_WAYBILL = """<style>
.waybill { font-family: Arial, Helvetica, sans-serif; font-size: 10px; color: #000; line-height: 1.25; }
.waybill table { border-collapse: collapse; width: 100%; }
.waybill .form-head td { border: 1px solid #000; padding: 2px 4px; vertical-align: top; }
.waybill .form-head .okud { text-align: right; width: 70px; }
.waybill .doc-box { margin: 6px 0; width: 220px; margin-left: auto; }
.waybill .doc-box td { border: 1px solid #000; padding: 2px 6px; text-align: center; }
.waybill .doc-box .lbl { font-size: 9px; background: #f5f5f5; }
.waybill h1 { font-size: 14px; text-align: center; margin: 8px 0 10px; letter-spacing: 1px; }
.waybill .parties td { border: 1px solid #000; padding: 3px 5px; vertical-align: top; }
.waybill .parties .lbl { width: 110px; font-weight: 700; background: #fafafa; }
.waybill .items { margin-top: 8px; font-size: 9px; }
.waybill .items th, .waybill .items td { border: 1px solid #000; padding: 2px 3px; }
.waybill .items th { background: #f0f0f0; font-weight: 700; text-align: center; vertical-align: middle; }
.waybill .c { text-align: center; }
.waybill .r { text-align: right; }
.waybill .items tfoot td { font-weight: 700; background: #fafafa; }
.waybill .words { margin: 8px 0 14px; font-weight: 700; font-size: 11px; }
.waybill .sign { margin-top: 10px; font-size: 10px; }
.waybill .sign td { border: none; padding: 4px 0; vertical-align: bottom; }
.waybill .sign .line { display: inline-block; min-width: 120px; border-bottom: 1px solid #000; margin: 0 4px; height: 16px; }
.waybill .sign .box { position: relative; min-height: 48px; }
.waybill .sign img.sig { max-height: 40px; vertical-align: middle; margin-left: 6px; }
.waybill .sign img.stamp { max-height: 72px; vertical-align: middle; margin-left: 6px; opacity: .85; }
.waybill .logo { max-height: 48px; margin-bottom: 6px; }
.waybill .note { font-size: 9px; color: #444; margin-top: 4px; }
</style>
<div class="waybill">
##LOGO_HTML##

<table class="form-head">
<tr>
<td>Унифицированная форма № ТОРГ-12<br>Утверждена постановлением Госкомстата России от 25.12.1998 № 132</td>
<td class="okud">Код<br><b>0330212</b></td>
</tr>
</table>

<table class="doc-box">
<tr>
<td class="lbl">Номер документа</td>
<td class="lbl">Дата составления</td>
</tr>
<tr>
<td><b>##DOC_NUMBER##</b></td>
<td><b>##DOC_DATE##</b></td>
</tr>
</table>

<h1>ТОВАРНАЯ НАКЛАДНАЯ</h1>

<table class="parties">
<tr><td class="lbl">Грузополучатель</td><td>##BUYER_FULL##</td></tr>
<tr><td class="lbl">Поставщик</td><td>##SELLER_FULL##</td></tr>
<tr><td class="lbl">Плательщик</td><td>##BUYER_FULL##</td></tr>
<tr><td class="lbl">Основание</td><td>##BASIS##</td></tr>
</table>

<table class="items">
<thead>
<tr>
<th rowspan="2" width="24">№</th>
<th rowspan="2">Товар, характеристика, артикул</th>
<th colspan="2">Единица измерения</th>
<th rowspan="2" width="48">Кол-во</th>
<th rowspan="2" width="62">Цена, руб.</th>
<th rowspan="2" width="72">Сумма без НДС, руб.</th>
<th colspan="2">НДС</th>
<th rowspan="2" width="72">Сумма с НДС, руб.</th>
</tr>
<tr>
<th width="36">наим.</th>
<th width="28">код</th>
<th width="52">ставка</th>
<th width="52">сумма</th>
</tr>
</thead>
<tbody>
<tr data-for="ITEMS">
<td class="c">##N##</td>
<td>##TITLE##</td>
<td class="c">##UNIT##</td>
<td class="c">-</td>
<td class="r">##QTY##</td>
<td class="r">##PRICE##</td>
<td class="r">##SUM##</td>
<td class="c">##VAT##</td>
<td class="r">0,00</td>
<td class="r">##SUM##</td>
</tr>
</tbody>
<tfoot>
<tr>
<td colspan="6" class="r">Итого</td>
<td class="r">##TOTAL##</td>
<td class="c">X</td>
<td class="r">0,00</td>
<td class="r">##TOTAL##</td>
</tr>
</tfoot>
</table>

<div class="words">Всего отпущено на сумму ##TOTAL_WORDS##</div>
<div class="note">В накладную включаются только товарные позиции (запчасти/товары), без услуг.</div>

<table class="sign" width="100%">
<tr>
<td width="50%">
<div class="box">Отпуск груза разрешил<span class="line"></span>##SIGNATURE_HTML####STAMP_HTML##<br>
<span style="padding-left:140px">##SELLER_DIRECTOR##</span></div>
</td>
<td width="50%">
<div class="box">Главный (старший) бухгалтер<span class="line"></span><br>
<span style="padding-left:180px">##SELLER_ACCOUNTANT##</span></div>
</td>
</tr>
<tr>
<td>
<div class="box">Отпуск груза произвел<span class="line"></span></div>
</td>
<td>
<div class="box">Груз получил грузополучатель<span class="line"></span></div>
</td>
</tr>
</table>
</div>
"""


def up():
    logger.info("Применение миграции 065_invoices_b2b")
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cur = conn.cursor()

        seller_cols = [
            ("bank_name", "bank_name TEXT"),
            ("bik", "bik TEXT"),
            ("checking_account", "checking_account TEXT"),
            ("corr_account", "corr_account TEXT"),
            ("kpp", "kpp TEXT"),
            ("ogrnip", "ogrnip TEXT"),
            ("legal_address", "legal_address TEXT"),
            ("director_title", "director_title TEXT"),
            ("director_name", "director_name TEXT"),
            ("accountant_name", "accountant_name TEXT"),
            ("signature_url", "signature_url TEXT"),
            ("stamp_url", "stamp_url TEXT"),
        ]
        for name, ddl in seller_cols:
            _add_column_if_missing(cur, "general_settings", name, ddl)

        customer_cols = [
            ("customer_kind", "customer_kind TEXT DEFAULT 'person'"),
            ("inn", "inn TEXT"),
            ("kpp", "kpp TEXT"),
            ("ogrn", "ogrn TEXT"),
            ("legal_name", "legal_name TEXT"),
            ("legal_address", "legal_address TEXT"),
            ("bank_name", "bank_name TEXT"),
            ("bik", "bik TEXT"),
            ("checking_account", "checking_account TEXT"),
            ("corr_account", "corr_account TEXT"),
        ]
        for name, ddl in customer_cols:
            _add_column_if_missing(cur, "customers", name, ddl)

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_type TEXT NOT NULL,
                year INTEGER NOT NULL,
                last_number INTEGER NOT NULL DEFAULT 0,
                UNIQUE(doc_type, year)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
                act_number INTEGER,
                waybill_number INTEGER,
                issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                due_date DATE,
                status TEXT NOT NULL DEFAULT 'unpaid',
                order_id INTEGER,
                customer_id INTEGER NOT NULL,
                buyer_kind TEXT,
                buyer_name TEXT,
                buyer_inn TEXT,
                buyer_kpp TEXT,
                buyer_ogrn TEXT,
                buyer_address TEXT,
                buyer_bank_name TEXT,
                buyer_bik TEXT,
                buyer_checking_account TEXT,
                buyer_corr_account TEXT,
                seller_snapshot TEXT,
                subtotal_cents INTEGER NOT NULL DEFAULT 0,
                vat_mode TEXT NOT NULL DEFAULT 'none',
                total_cents INTEGER NOT NULL DEFAULT 0,
                comment TEXT,
                paid_at TIMESTAMP,
                paid_by_user_id INTEGER,
                payment_id INTEGER,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (payment_id) REFERENCES payments(id),
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (paid_by_user_id) REFERENCES users(id)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_order ON invoices(order_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_invoices_issued ON invoices(issued_at DESC)")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                line_type TEXT NOT NULL DEFAULT 'service',
                title TEXT NOT NULL,
                qty REAL NOT NULL DEFAULT 1,
                unit TEXT NOT NULL DEFAULT 'шт',
                price_cents INTEGER NOT NULL DEFAULT 0,
                sum_cents INTEGER NOT NULL DEFAULT 0,
                vat_label TEXT NOT NULL DEFAULT 'Без НДС',
                source_order_service_id INTEGER,
                source_order_part_id INTEGER,
                position INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id)"
        )

        _add_column_if_missing(cur, "payments", "invoice_id", "invoice_id INTEGER")
        try:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id)"
            )
        except Exception:
            pass

        templates = [
            ("invoice_bill", "Счёт на оплату (B2B)", DEFAULT_INVOICE_BILL),
            ("invoice_act", "Акт выполненных работ (B2B)", DEFAULT_INVOICE_ACT),
            ("invoice_waybill", "Товарная накладная (B2B)", DEFAULT_INVOICE_WAYBILL),
        ]
        for ttype, name, html in templates:
            cur.execute(
                "SELECT id FROM print_templates WHERE template_type = ?", (ttype,)
            )
            if cur.fetchone():
                continue
            cur.execute(
                """
                INSERT INTO print_templates (name, template_type, html_content)
                VALUES (?, ?, ?)
                """,
                (name, ttype, html),
            )

        new_permissions = [
            ("view_invoices", "Просмотр раздела Счета"),
            ("manage_invoices", "Создание и редактирование счетов"),
            ("mark_invoice_paid", "Отметка счетов оплаченными"),
        ]
        for name, desc in new_permissions:
            cur.execute(
                "INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)",
                (name, desc),
            )
        cur.execute(
            "SELECT id, name FROM permissions WHERE name IN (?, ?, ?)",
            [p[0] for p in new_permissions],
        )
        perm_ids = {name: pid for pid, name in cur.fetchall()}
        role_map = {
            "admin": ["view_invoices", "manage_invoices", "mark_invoice_paid"],
            "manager": ["view_invoices", "manage_invoices", "mark_invoice_paid"],
            "viewer": ["view_invoices"],
        }
        for role, names in role_map.items():
            for pname in names:
                pid = perm_ids.get(pname)
                if not pid:
                    continue
                cur.execute(
                    "INSERT OR IGNORE INTO role_permissions (role, permission_id) VALUES (?, ?)",
                    (role, pid),
                )

        conn.commit()
    logger.info("Миграция 065_invoices_b2b успешно применена")


def down():
    logger.warning("Откат миграции 065_invoices_b2b (частичный)")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS invoice_items")
        cur.execute("DROP TABLE IF EXISTS invoices")
        cur.execute("DROP TABLE IF EXISTS invoice_sequences")
        conn.commit()
