"""Одноразово: HTML счёта в стиле Т-Банк/1С → print_templates.invoice_bill."""
from dotenv import load_dotenv

load_dotenv()

from app.services.settings_service import SettingsService

HTML = """<style>
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

if __name__ == "__main__":
    ok = SettingsService.save_print_template("invoice_bill", HTML, name="Счёт на оплату")
    tpl = SettingsService.get_print_template_fresh("invoice_bill")
    content = (tpl or {}).get("html_content") or ""
    print("saved:", ok)
    print("len:", len(content))
    print("style ok:", "<style>" in content and "&lt;style&gt;" not in content)
    print("bank ok:", "Банк получателя" in content)
    print("items ok:", 'data-for="ITEMS"' in content)
    print("thead ok:", "<thead>" in content)
