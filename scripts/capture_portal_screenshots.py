"""
Capture customer portal screenshots for docs.

Default target is public demo:
  python scripts/capture_portal_screenshots.py

Локально (только новые кадры кабинета):
  python scripts/capture_portal_screenshots.py --base-url http://127.0.0.1:5000 \
      --staff-user admin --staff-password 111111 --only 47,48,49
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "walkthrough"

# Пары «страница кабинета» должны отличаться: одинаковые байты означают,
# что вход не удался и снят экран логина.
CABINET_SHOTS = (
    "29-portal-login.png",
    "34-portal-dashboard.png",
    "35-portal-orders.png",
    "36-portal-payments.png",
    "37-portal-devices.png",
    "38-portal-wallet.png",
)

# Кадры новых блоков кабинета (диагностика, чек, заявки по устройству)
DIAG_SHOT = "47-portal-order-diagnostics.png"
RECEIPT_SHOT = "48-portal-receipt.png"
DEVICE_ORDERS_SHOT = "49-portal-device-orders.png"


def _find_duplicates(out: Path, names: tuple[str, ...]) -> list[list[str]]:
    by_digest: dict[str, list[str]] = {}
    for name in names:
        path = out / name
        if not path.exists():
            continue
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        by_digest.setdefault(digest, []).append(name)
    return [group for group in by_digest.values() if len(group) > 1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Nika CRM customer portal screenshots")
    parser.add_argument("--base-url", default="https://service.nika-crm.ru")
    parser.add_argument("--staff-user", default="demo_admin")
    parser.add_argument("--staff-password", default="Demo2026!")
    parser.add_argument("--portal-password", default="Portal123!")
    parser.add_argument(
        "--customer-id",
        type=int,
        default=None,
        help="Клиент для съёмки кабинета. По умолчанию берётся владелец заявки "
             "с заполненной диагностикой, иначе первый из /clients.",
    )
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument(
        "--only",
        default="",
        help="Снять только кадры, чьи имена содержат одну из подстрок через запятую "
             "(например 47,48,49). Пусто — снимать всё.",
    )
    args = parser.parse_args()
    only = [part.strip() for part in args.only.split(",") if part.strip()]

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            locale="ru-RU",
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        def shot(name: str) -> None:
            if only and not any(part in name for part in only):
                return
            path = out / name
            page.screenshot(path=str(path), full_page=False)
            print("saved", path)

        def goto(path: str, wait_ms: int = 1200) -> None:
            url = f"{base}{path}" if path.startswith("/") else path
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(wait_ms)

        # 29: portal login page
        goto("/portal/login", wait_ms=1500)
        shot("29-portal-login.png")

        # Staff login to prepare customer credentials for portal
        goto("/login", wait_ms=1200)
        if not page.locator("input[name='username']").count():
            goto("/?login=1", wait_ms=1200)
            form_user = page.locator("#demoLoginForm input[name='username']")
            if not form_user.count():
                raise RuntimeError("Staff login form not found")
            form_user.fill(args.staff_user)
            page.locator("#demoLoginForm input[name='password']").fill(args.staff_password)
            page.locator("#demoLoginForm button[type='submit']").click()
        else:
            page.locator("input[name='username']").fill(args.staff_user)
            page.locator("input[name='password']").fill(args.staff_password)
            page.locator("button[type='submit']").click()
        page.wait_for_timeout(2500)

        # Clients list screenshot
        goto("/clients", wait_ms=1800)
        shot("30-portal-clients-list.png")

        def customer_with_diagnostics() -> str:
            """Клиент, у которого есть заявка с заполненной диагностикой."""
            try:
                resp = page.request.post(
                    f"{base}/api/datatables/orders",
                    form={
                        "draw": "1",
                        "start": "0",
                        "length": "40",
                        "order[0][column]": "0",
                        "order[0][dir]": "desc",
                    },
                )
                ids = re.findall(r"/order/(\d+)", resp.text())
                ids += re.findall(r'"DT_RowId"\s*:\s*"?(\d+)"?', resp.text())
            except Exception as e:
                print("WARN: orders list for diagnostics failed:", e)
                return ""
            seen: list[str] = []
            for oid in ids:
                if oid in seen:
                    continue
                seen.append(oid)
                try:
                    diag = page.request.get(f"{base}/api/order/{oid}/diagnostics")
                    payload = diag.json() if diag.ok else {}
                except Exception:
                    continue
                if not (payload.get("diagnostics") or "").strip():
                    continue
                goto(f"/order/{oid}", wait_ms=1200)
                m_cust = re.search(r"/clients/(\d+)", page.content())
                if m_cust:
                    print("order with diagnostics", oid, "customer", m_cust.group(1))
                    return f"/clients/{m_cust.group(1)}"
            return ""

        # Open client card
        if args.customer_id:
            href = f"/clients/{args.customer_id}"
        else:
            href = customer_with_diagnostics()
            if not href:
                goto("/clients", wait_ms=1500)
                for a in page.locator("a[href*='/clients/']").all():
                    link = a.get_attribute("href") or ""
                    if re.search(r"/clients/\d+$", link):
                        href = link
                        break
            if not href:
                raise RuntimeError("Could not find client detail link on /clients")

        goto(href if href.startswith("/") else f"/{href}", wait_ms=1800)
        shot("31-portal-client-card.png")

        # Extract customer id and phone from detail page
        m = re.search(r"/clients/(\d+)", page.url)
        if not m:
            raise RuntimeError(f"Cannot parse customer id from URL: {page.url}")
        customer_id = int(m.group(1))

        phone = (
            page.locator("#editCustomerPhone").input_value().strip()
            if page.locator("#editCustomerPhone").count()
            else ""
        )
        if not phone:
            raise RuntimeError("Customer phone is empty; choose another customer with phone")

        csrf = (
            page.locator("meta[name='csrf-token']").get_attribute("content") or ""
            if page.locator("meta[name='csrf-token']").count()
            else ""
        )
        if not csrf:
            raise RuntimeError("CSRF token not found on customer page")

        # Set portal password for this customer
        set_result = page.evaluate(
            """async ({cid, password, csrf}) => {
                const res = await fetch(`/api/customers/${cid}/portal-password`, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrf,
                        'X-CSRF-Token': csrf,
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({password}),
                });
                let payload = null;
                try { payload = await res.json(); } catch (e) {}
                return {ok: res.ok, status: res.status, payload};
            }""",
            {"cid": customer_id, "password": args.portal_password, "csrf": csrf},
        )
        if not set_result.get("ok"):
            raise RuntimeError(
                f"Failed to set portal password: {set_result.get('status')} {set_result.get('payload')}"
            )

        # Portal password lives inside the edit modal, so open it for the screenshot
        goto(f"/clients/{customer_id}", wait_ms=1500)
        page.locator("button[data-bs-target='#editCustomerModal']").first.click()
        page.wait_for_selector("#editCustomerModal.show", timeout=15000)
        page.wait_for_timeout(800)
        shot("32-portal-password-issued.png")

        # Portal login with customer creds
        goto("/portal/login", wait_ms=1200)
        page.locator("input[name='phone']").fill(phone)
        page.locator("input[name='password']").fill(args.portal_password)
        shot("33-portal-login-filled.png")
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1800)

        # First login forces a password change: the form asks for the current
        # password again (phone stays readonly), and leaving it empty silently
        # blocks the submit.
        if page.locator("input[name='new_password']").count():
            page.locator("input[name='password']").fill(args.portal_password)
            page.locator("input[name='new_password']").fill(args.portal_password)
            page.locator("input[name='new_password_confirm']").fill(args.portal_password)
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(2000)

        if "/portal/login" in page.url:
            raise RuntimeError(
                f"Portal login failed, still on {page.url}. "
                "Screenshots would show the login page instead of the customer cabinet."
            )

        # Customer portal pages
        goto("/portal/dashboard", wait_ms=1500)
        if "/portal/login" in page.url:
            raise RuntimeError("Portal session lost before dashboard screenshot")
        shot("34-portal-dashboard.png")

        goto("/portal/orders", wait_ms=1500)
        shot("35-portal-orders.png")

        def open_order_modal() -> bool:
            row = page.locator(".order-row, .order-link").first
            if not row.count():
                return False
            row.click()
            try:
                page.wait_for_selector("#orderModalContent:not(.d-none)", timeout=20000)
            except Exception:
                return False
            page.wait_for_timeout(900)
            return True

        # 40: детали заявки в кабинете — диагностика с фото
        if open_order_modal():
            diag = page.locator("#modalDiagnostics")
            if diag.count():
                diag.scroll_into_view_if_needed()
                page.wait_for_timeout(400)
            shot(DIAG_SHOT)

            # Чек: window.print() в headless блокирует — собираем HTML и снимаем отдельной страницей
            page.evaluate("window.print = function () {};")
            page.locator("#btnPrintReceipt").click()
            page.wait_for_timeout(600)
            receipt_html = page.evaluate(
                """() => {
                    const area = document.getElementById('printReceiptArea');
                    return area ? area.innerHTML : '';
                }"""
            )
            if receipt_html and (not only or any(p in RECEIPT_SHOT for p in only)):
                rec_page = context.new_page()
                rec_page.set_content(
                    "<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
                    "<style>"
                    "html,body{margin:0;background:#fff;}"
                    "body{padding:28px;}"
                    ".portal-receipt{font-family:'Courier New',monospace;font-size:13px;"
                    "max-width:420px;margin:0 auto;color:#111;}"
                    ".portal-receipt table{width:100%;border-collapse:collapse;}"
                    ".portal-receipt td{padding:4px 8px;text-align:left;border-bottom:1px dashed #ccc;}"
                    ".portal-receipt .receipt-header{text-align:center;font-weight:bold;"
                    "margin-bottom:12px;border-bottom:2px solid #000;padding-bottom:8px;}"
                    ".portal-receipt .receipt-footer{margin-top:12px;border-top:2px solid #000;"
                    "padding-top:8px;text-align:center;font-size:10px;color:#666;}"
                    "</style></head><body>"
                    + receipt_html
                    + "</body></html>"
                )
                rec_page.wait_for_timeout(400)
                rec_page.screenshot(path=str(out / RECEIPT_SHOT), full_page=True)
                rec_page.close()
                print("saved", out / RECEIPT_SHOT)
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
        else:
            print("WARN: order modal not opened — skipped", DIAG_SHOT, RECEIPT_SHOT)

        goto("/portal/payments", wait_ms=1500)
        shot("36-portal-payments.png")

        goto("/portal/devices", wait_ms=1500)
        shot("37-portal-devices.png")

        # 42: заявки по устройству — та же карточка заявки открывается из строки
        if open_order_modal():
            shot(DEVICE_ORDERS_SHOT)
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        else:
            print("WARN: device order modal not opened — skipped", DEVICE_ORDERS_SHOT)

        goto("/portal/wallet", wait_ms=1500)
        shot("38-portal-wallet.png")

        browser.close()

    duplicates = _find_duplicates(out, CABINET_SHOTS)
    if duplicates:
        raise RuntimeError(
            "Identical portal screenshots detected: "
            + "; ".join(" == ".join(group) for group in duplicates)
            + ". This usually means the portal session was not established."
        )

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
