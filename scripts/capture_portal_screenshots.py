"""
Capture customer portal screenshots for docs.

Default target is public demo:
  python scripts/capture_portal_screenshots.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "walkthrough"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Nika CRM customer portal screenshots")
    parser.add_argument("--base-url", default="https://demo.nika-sc.ru")
    parser.add_argument("--staff-user", default="demo_admin")
    parser.add_argument("--staff-password", default="Demo2026!")
    parser.add_argument("--portal-password", default="Portal123!")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

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

        # Open first client card from /clients/<id>
        href = ""
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

        # Show customer detail with portal block after password set
        goto(f"/clients/{customer_id}", wait_ms=1500)
        shot("32-portal-password-issued.png")

        # Portal login with customer creds
        goto("/portal/login", wait_ms=1200)
        page.locator("input[name='phone']").fill(phone)
        page.locator("input[name='password']").fill(args.portal_password)
        shot("33-portal-login-filled.png")
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1800)

        # First login requires password change
        if page.locator("input[name='new_password']").count():
            page.locator("input[name='new_password']").fill(args.portal_password)
            page.locator("input[name='new_password_confirm']").fill(args.portal_password)
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(1800)

        # Customer portal pages
        goto("/portal/dashboard", wait_ms=1500)
        shot("34-portal-dashboard.png")

        goto("/portal/orders", wait_ms=1500)
        shot("35-portal-orders.png")

        goto("/portal/payments", wait_ms=1500)
        shot("36-portal-payments.png")

        goto("/portal/devices", wait_ms=1500)
        shot("37-portal-devices.png")

        goto("/portal/wallet", wait_ms=1500)
        shot("38-portal-wallet.png")

        browser.close()

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
