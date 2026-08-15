# Скриншоты для USER_WALKTHROUGH.md

В каталоге лежат PNG (`01-login.png` … `38-portal-wallet.png`), снятые с работающей CRM.

Они уже встроены в [USER_WALKTHROUGH.md](../../USER_WALKTHROUGH.md). При обновлении UI переснимите:

```bash
python scripts/capture_walkthrough_screenshots.py --base-url http://127.0.0.1:5000 --user admin --password 111111
```

Счета B2B: `24-invoices-list.png` … `28-invoice-create.png`.
Портал клиента: `29-portal-login.png` … `38-portal-wallet.png`.

SMTP / почта (иллюстрации гайда § 13.5): `39-smtp-mailru-correct.png`, `40-smtp-sender-mismatch.png`, `41-smtp-checklist.png`.

PWA (гайд § 18 и блог): `42-pwa-chrome-install.png` … `45-pwa-mobile-add-home.png`.

Диагностика и кабинет (блог 27–28): `46-order-diagnostics.png`, `47-portal-order-diagnostics.png`, `48-portal-receipt.png`, `49-portal-device-orders.png`.

```bash
python scripts/seed_blog_shot_order.py
python scripts/capture_walkthrough_screenshots.py --base-url http://127.0.0.1:5000 --user admin --password 111111 --order-id <order_id> --only 46-order-diagnostics
python scripts/capture_portal_screenshots.py --base-url http://127.0.0.1:5000 --staff-user admin --staff-password 111111 --customer-id <customer_id> --only 35,36,37,47,48,49
```

```bash
python scripts/capture_pwa_screenshots.py
```

Отдельная съёмка портала (подготовка пароля в CRM + вход клиента):

```bash
python scripts/capture_portal_screenshots.py --customer-id 2
```

Указывайте `--customer-id` клиента с заявками и платежами, иначе разделы кабинета будут пустыми.

Скрипт сам проверяет, что вход в портал состоялся (`/portal/dashboard`) и что снимки кабинета не совпадают побайтово. Если проверка падает — значит снялся экран логина, а не кабинет; публиковать такие файлы нельзя.

Снимать только на демо-данных: кадры `30`–`32` показывают список и карточку клиента, поэтому боевая база с реальными ФИО и телефонами не годится. Локально это разворачивается так:

```bash
psql -d nikacrm_shots -f database/bootstrap/nikacrm_public_sanitized.sql
DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/nikacrm_shots NIKA_DEMO_SEED_CONFIRM=YES \
  python scripts/seed_demo_bulk.py --yes --orders 120 --customers 60 --staff-users 12 --parts 40
```

Учётка для съёмки — `demo_admin` / `Demo2026!`.
