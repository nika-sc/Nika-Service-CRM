"""
Съёмка скриншотов для docs/USER_WALKTHROUGH.md с DEMO/локальной CRM.

Пример (демо):
  python scripts/capture_walkthrough_screenshots.py --base-url https://service.nika-crm.ru --user demo_admin --password Demo2026!
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "walkthrough"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Nika CRM walkthrough screenshots")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="111111")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--order-id", default="", help="Optional order id to open")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")
    shots: list[str] = []

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
            path = out / name
            page.screenshot(path=str(path), full_page=False)
            shots.append(path.name)
            print("saved", path)

        def goto(path: str, wait_ms: int = 1000, retries: int = 4) -> None:
            url = f"{base}{path}" if path.startswith("/") else path
            last_err: Exception | None = None
            for attempt in range(1, retries + 1):
                try:
                    page.goto(url, wait_until="commit", timeout=90000)
                    try:
                        page.wait_for_load_state("domcontentloaded", timeout=45000)
                    except Exception:
                        pass
                    page.wait_for_timeout(wait_ms)
                    return
                except Exception as e:
                    last_err = e
                    print(f"goto retry {attempt}/{retries}: {url} -> {e}")
                    time.sleep(2 * attempt)
            raise last_err  # type: ignore[misc]

        def dismiss_flash() -> None:
            btn = page.locator(".alert .btn-close, .btn-close").first
            try:
                if btn.count() and btn.is_visible():
                    btn.click(timeout=800)
                    page.wait_for_timeout(200)
            except Exception:
                pass

        # Login — сначала /login (локальный CRM без PUBLIC_LANDING)
        goto("/login", wait_ms=1200)
        if page.locator("input[name='username']").count():
            page.locator("input[name='username']").fill(args.user)
            page.locator("input[name='password']").fill(args.password)
            shot("01-login.png")
            page.locator("button[type='submit']").click()
        else:
            goto("/?login=1", wait_ms=1500)
            form_user = page.locator("#demoLoginForm input[name='username']")
            if form_user.count():
                form_user.fill(args.user)
                page.locator("#demoLoginForm input[name='password']").fill(args.password)
                shot("01-login.png")
                page.locator("#demoLoginForm button[type='submit']").click()
            else:
                raise RuntimeError("Login form not found at /login or /?login=1")
        page.wait_for_timeout(2500)
        dismiss_flash()
        shot("02-dashboard.png")

        goto("/add_order", wait_ms=1500)
        dismiss_flash()
        shot("03-add-order.png")

        # Resolve order id
        order_id = (args.order_id or "").strip()
        if not order_id:
            # DataTables JSON
            try:
                resp = page.request.get(
                    f"{base}/api/datatables/orders",
                    params={"draw": "1", "start": "0", "length": "10"},
                )
                body = resp.text()
                m = re.search(r'"DT_RowId"\s*:\s*"?(\d+)"?', body) or re.search(
                    r'"id"\s*:\s*(\d+)', body
                )
                if m:
                    order_id = m.group(1)
                    print("order from API GET", order_id)
            except Exception as e:
                print("API GET orders failed:", e)
        if not order_id:
            try:
                resp = page.request.post(
                    f"{base}/api/datatables/orders",
                    form={
                        "draw": "1",
                        "start": "0",
                        "length": "10",
                        "order[0][column]": "0",
                        "order[0][dir]": "desc",
                    },
                )
                body = resp.text()
                print("API POST status", resp.status, body[:200])
                found = re.findall(r"/order/(\d+)", body)
                found += re.findall(r'"DT_RowId"\s*:\s*"?(\d+)"?', body)
                found += re.findall(r'"id"\s*:\s*(\d+)', body)
                if found:
                    order_id = found[0]
                    print("order from API POST", order_id)
            except Exception as e:
                print("API POST orders failed:", e)
        if not order_id:
            goto("/all_orders?view=kanban", wait_ms=3500)
            found = re.findall(r"/order/(\d+)", page.content())
            if found:
                order_id = found[0]
                print("order from kanban", order_id)

        if order_id:
            goto(f"/order/{order_id}", wait_ms=2500, retries=5)
            # wait for key section (heavy pages)
            try:
                page.wait_for_selector("text=Товары и услуги", timeout=90000)
            except Exception:
                print("WARN: order page loaded without items marker")
            dismiss_flash()
            shot("04-order-detail.png")

            try:
                page.locator("text=Товары и услуги").first.scroll_into_view_if_needed()
                page.wait_for_timeout(400)
            except Exception:
                pass
            shot("07-order-items.png")

            # Open items editor
            opened_items = False
            for sel in (
                "button:has-text('Добавить')",
                "#btnAddItems",
                "[data-action='add-items']",
                "button.btn-add-item",
            ):
                btns = page.locator(sel)
                n = btns.count()
                for i in range(min(n, 6)):
                    try:
                        btn = btns.nth(i)
                        if not btn.is_visible():
                            continue
                        btn.click(timeout=1500)
                        page.wait_for_timeout(900)
                        if page.locator("#itemsCategoriesContainer, #itemsHomeView, text=Услуги").count():
                            opened_items = True
                            break
                        page.keyboard.press("Escape")
                    except Exception:
                        continue
                if opened_items:
                    break
            if opened_items:
                svc = page.locator("text=Услуги").first
                if svc.count():
                    try:
                        svc.click()
                        page.wait_for_timeout(500)
                    except Exception:
                        pass
                shot("05-add-service.png")
                part = page.locator("text=Товары").first
                if part.count():
                    try:
                        part.click()
                        page.wait_for_timeout(500)
                    except Exception:
                        pass
                shot("06-add-part.png")
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
            else:
                print("WARN: items editor not opened (05/06)")

            try:
                page.locator("text=Платежи").first.scroll_into_view_if_needed()
                page.wait_for_timeout(400)
            except Exception:
                pass
            shot("09-order-payments.png")

            pay_btn = page.locator("button:has-text('Добавить оплату')").first
            if pay_btn.count():
                try:
                    pay_btn.click()
                    page.wait_for_timeout(800)
                    shot("08-add-payment.png")
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(300)
                except Exception as e:
                    print("WARN payment modal:", e)

            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(300)
            shot("10-change-status.png")

            for sel in (
                "button:has-text('Закрыт')",
                "button:has-text('Закрыта')",
                ".order-status button",
                "button.dropdown-toggle",
            ):
                st = page.locator(sel).first
                if st.count():
                    try:
                        st.click(timeout=1500)
                        page.wait_for_timeout(600)
                        shot("11-close-order.png")
                        page.keyboard.press("Escape")
                        break
                    except Exception:
                        continue

            for sel in ("button:has-text('Печать')", "a:has-text('Печать')", "#printOrderBtn"):
                pr = page.locator(sel).first
                if pr.count():
                    try:
                        pr.click(timeout=1500)
                        page.wait_for_timeout(700)
                        shot("12-print-modal.png")
                        page.keyboard.press("Escape")
                        break
                    except Exception:
                        continue
        else:
            print("WARN: no order id — skipped 04-12")

        goto("/salary", wait_ms=1500)
        shot("13-salary-dashboard.png")

        emp = page.locator("a[href*='/salary/employee/']").first
        if emp.count():
            href = emp.get_attribute("href") or ""
            if href.startswith("/"):
                goto(href, wait_ms=1200)
            elif href:
                goto(href if href.startswith("http") else f"/{href}", wait_ms=1200)
            shot("14-salary-accruals.png")
            tab = page.locator("a:has-text('Выплаты'), button:has-text('Выплаты')").first
            if tab.count():
                tab.click()
                page.wait_for_timeout(700)
                shot("16-salary-payments-list.png")
            payout = page.locator(
                "button:has-text('Зарегистрировать выплату'), a:has-text('Зарегистрировать выплату')"
            ).first
            if payout.count():
                try:
                    payout.click()
                    page.wait_for_timeout(800)
                    shot("15-salary-payout.png")
                    page.keyboard.press("Escape")
                except Exception as e:
                    print("WARN payout:", e)
            else:
                goto("/salary", wait_ms=1000)
                pay = page.locator("a:has-text('К выплате'), button:has-text('К выплате')").first
                if pay.count():
                    try:
                        pay.click()
                        page.wait_for_timeout(1000)
                        shot("15-salary-payout.png")
                        page.keyboard.press("Escape")
                    except Exception as e:
                        print("WARN payout btn:", e)

        goto("/finance/cash", wait_ms=1500)
        shot("17-finance-cash.png")
        income = page.locator("button:has-text('Приход')").first
        if income.count():
            try:
                income.click()
                page.wait_for_timeout(700)
                shot("18-cash-manual.png")
                page.keyboard.press("Escape")
            except Exception as e:
                print("WARN cash:", e)

        goto("/reports/day", wait_ms=1500)
        shot("19-report-day.png")
        goto("/reports/cash", wait_ms=1500)
        shot("20-report-cash.png")
        goto("/shop", wait_ms=1200)
        shot("21-shop.png")
        goto("/warehouse/purchases", wait_ms=1200)
        shot("22-purchases.png")

        goto("/", wait_ms=1200)
        chat = page.locator("#staffChatFab")
        if chat.count():
            try:
                chat.click()
                page.wait_for_timeout(1000)
                shot("23-staff-chat.png")
            except Exception as e:
                print("WARN chat:", e)

        # --- Счета B2B ---
        goto("/invoices", wait_ms=1500)
        shot("24-invoices-list.png")
        goto("/invoices/settings", wait_ms=1500)
        shot("25-invoice-settings.png")
        inv_link = page.locator("a[href*='/invoices/']").filter(has_not=page.locator("[href$='/settings'], [href$='/new']")).first
        invoice_id = ""
        try:
            goto("/invoices", wait_ms=1000)
            for a in page.locator("a[href*='/invoices/']").all():
                href = a.get_attribute("href") or ""
                m = re.search(r"/invoices/(\d+)(?:/|$)", href)
                if m:
                    invoice_id = m.group(1)
                    break
        except Exception as e:
            print("WARN find invoice:", e)
        if invoice_id:
            goto(f"/invoices/{invoice_id}", wait_ms=1500)
            shot("26-invoice-detail.png")
            goto(f"/invoices/{invoice_id}/print/bill", wait_ms=1500)
            shot("27-invoice-print-bill.png")
        else:
            print("WARN: no invoice id — skipped 26-27")
        goto("/invoices/new", wait_ms=1500)
        shot("28-invoice-create.png")

        browser.close()

    names = {
        "01-login.png", "02-dashboard.png", "03-add-order.png", "04-order-detail.png",
        "05-add-service.png", "06-add-part.png", "07-order-items.png", "08-add-payment.png",
        "09-order-payments.png", "10-change-status.png", "11-close-order.png", "12-print-modal.png",
        "13-salary-dashboard.png", "14-salary-accruals.png", "15-salary-payout.png",
        "16-salary-payments-list.png", "17-finance-cash.png", "18-cash-manual.png",
        "19-report-day.png", "20-report-cash.png", "21-shop.png", "22-purchases.png",
        "23-staff-chat.png",
        "24-invoices-list.png", "25-invoice-settings.png", "26-invoice-detail.png",
        "27-invoice-print-bill.png", "28-invoice-create.png",
    }
    missing = sorted(names - {p.name for p in out.glob("*.png")})
    print("Done. Captured this run:", len(shots))
    if missing:
        print("Still missing:", ", ".join(missing))
    else:
        print("All expected PNGs present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
