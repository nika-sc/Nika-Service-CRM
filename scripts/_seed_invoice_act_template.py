"""HTML акта выполненных работ в стиле Т-Банк/1С → print_templates.invoice_act."""
from dotenv import load_dotenv

load_dotenv()

from app.services.settings_service import SettingsService

HTML = """<style>
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

if __name__ == "__main__":
    ok = SettingsService.save_print_template("invoice_act", HTML)
    tpl = SettingsService.get_print_template_fresh("invoice_act")
    content = (tpl or {}).get("html_content") or ""
    print("saved:", ok)
    print("len:", len(content))
    print("title ok:", "Акт №" in content)
    print("service col ok:", ">Услуга<" in content)
    print("disclaimer ok:", "Вышеперечисленные услуги" in content)
    print("sign ok:", "Заказчик" in content and "Исполнитель" in content)
