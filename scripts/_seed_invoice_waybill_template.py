"""HTML товарной накладной (ТОРГ-12) → print_templates.invoice_waybill."""
from dotenv import load_dotenv

load_dotenv()

from app.services.settings_service import SettingsService

HTML = """<style>
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

if __name__ == "__main__":
    ok = SettingsService.save_print_template("invoice_waybill", HTML)
    tpl = SettingsService.get_print_template_fresh("invoice_waybill")
    content = (tpl or {}).get("html_content") or ""
    print("saved:", ok)
    print("len:", len(content))
    print("torg12 ok:", "0330212" in content)
    print("title ok:", "ТОВАРНАЯ НАКЛАДНАЯ" in content)
    print("parties ok:", "Грузополучатель" in content and "Поставщик" in content)
    print("items ok:", 'data-for="ITEMS"' in content)
    print("tfoot ok:", "<tfoot>" in content)
