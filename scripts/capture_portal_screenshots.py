"""
Capture customer portal screenshots for docs.

Default target is public demo:
  python scripts/capture_portal_screenshots.py
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
    parser.add_argument("--base-url", default="https://demo.nika-sc.ru")
    parser.add_argument("--staff-user", default="demo_admin")
    parser.add_argument("--staff-password", default="Demo2026!")
    parser.add_argument("--portal-password", default="Portal123!")
    parser.add_argument(
        "--customer-id",
        type=int,
        default=None,
        help="Клиент для съёмки кабинета. По умолчанию первый из /clients, "
             "но у него может не быть заявок и платежей.",
    )
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

        # Open client card
        if args.customer_id:
            href = f"/clients/{args.customer_id}"
        else:
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

        goto("/portal/payments", wait_ms=1500)
        shot("36-portal-payments.png")

        goto("/portal/devices", wait_ms=1500)
        shot("37-portal-devices.png")

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
