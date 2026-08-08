# Скриншоты для USER_WALKTHROUGH.md

В каталоге лежат PNG (`01-login.png` … `38-portal-wallet.png`), снятые с работающей CRM.

Они уже встроены в [USER_WALKTHROUGH.md](../../USER_WALKTHROUGH.md). При обновлении UI переснимите:

```bash
python scripts/capture_walkthrough_screenshots.py --base-url http://127.0.0.1:5000 --user admin --password 111111
```

Счета B2B: `24-invoices-list.png` … `28-invoice-create.png`.
Портал клиента: `29-portal-login.png` … `38-portal-wallet.png`.

Отдельная съёмка портала (подготовка пароля в CRM + вход клиента):

```bash
python scripts/capture_portal_screenshots.py
```
