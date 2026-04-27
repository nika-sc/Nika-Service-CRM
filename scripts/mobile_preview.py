"""
Эмуляция мобильного вида CRM.
Открывает браузер с viewport телефона для ручной проверки.

Использование:
    # Запустить Flask: python run.py (в другом терминале)

    # Интерактивный режим — браузер остаётся открытым:
    python scripts/mobile_preview.py --interactive

    # Скриншоты в папку mobile_screenshots:
    python scripts/mobile_preview.py

    # Свой URL и устройства:
    python scripts/mobile_preview.py -i --url http://192.168.1.100:5000 --devices iphone14
"""
import argparse
import os
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Установите Playwright: pip install playwright && playwright install chromium")
    exit(1)

DEVICES = {
    'iphone14': {'width': 390, 'height': 844, 'ua': 'iPhone'},
    'iphone_se': {'width': 375, 'height': 667, 'ua': 'iPhone SE'},
    'android': {'width': 360, 'height': 740, 'ua': 'Android'},
    'pixel': {'width': 412, 'height': 915, 'ua': 'Pixel'},
}
OUTPUT_DIR = Path(__file__).parent.parent / 'mobile_screenshots'


def run_interactive(url: str, device: str) -> None:
    cfg = DEVICES.get(device, DEVICES['iphone14'])
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': cfg['width'], 'height': cfg['height']},
            user_agent=f"Mozilla/5.0 ({cfg['ua']}; Mobile) AppleWebKit/537.36",
            is_mobile=True,
            has_touch=True,
        )
        page = context.new_page()
        page.goto(url, wait_until='domcontentloaded')
        print(f"Браузер открыт: {device} ({cfg['width']}×{cfg['height']})")
        print("Закройте окно браузера или Ctrl+C для выхода.")
        try:
            page.wait_for_timeout(3600 * 1000)
        except KeyboardInterrupt:
            pass
        context.close()
        browser.close()


def run_screenshots(url: str, devices: list, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = [('/login', 'Логин'), ('/', 'Главная'), ('/all_orders', 'Заявки')]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for dev in devices:
            cfg = DEVICES.get(dev, DEVICES['iphone14'])
            ctx = browser.new_context(viewport={'width': cfg['width'], 'height': cfg['height']},
                                      is_mobile=True, has_touch=True)
            page = ctx.new_page()
            for path, label in pages:
                try:
                    page.goto(f"{url.rstrip('/')}{path}", wait_until='domcontentloaded', timeout=15000)
                    page.wait_for_timeout(1500)
                    slug = path.strip('/') or 'home'
                    fname = output_dir / f"{dev}_{slug}.png"
                    page.screenshot(path=fname)
                    print(f"  {dev} {label}: {fname.name}")
                except Exception as e:
                    print(f"  {dev} {label}: {e}")
            ctx.close()
        browser.close()
    print(f"\nСкриншоты: {output_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-i', '--interactive', action='store_true')
    ap.add_argument('--url', default='http://127.0.0.1:5000')
    ap.add_argument('--devices', default='iphone14,android')
    ap.add_argument('--output', type=Path, default=OUTPUT_DIR)
    args = ap.parse_args()
    devices = [d.strip() for d in args.devices.split(',') if d.strip()] or ['iphone14']

    if args.interactive:
        run_interactive(args.url, devices[0])
    else:
        run_screenshots(args.url, devices, args.output)


if __name__ == '__main__':
    main()
