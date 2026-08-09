"""
Съёмка иллюстраций PWA для USER_GUIDE §18 и блога (без логина на демо).

  python scripts/capture_pwa_screenshots.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "walkthrough"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture PWA install doc screenshots")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headled=False) if False else p.chromium.launch(headless=True)

        # 42 + 43: Chrome-like install affordance over CRM-looking page
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ru-RU")
        page = context.new_page()
        page.set_content(
            """
<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>
  html,body{margin:0;font-family:system-ui,Segoe UI,sans-serif;background:#0f1720;color:#e8eef7}
  #bar{position:fixed;top:0;left:0;right:0;height:48px;z-index:9;display:flex;align-items:center;gap:12px;
    padding:0 16px;background:#202124;box-shadow:0 2px 8px rgba(0,0,0,.35)}
  #bar .url{flex:1;background:#303134;border-radius:16px;padding:7px 14px;color:#bdc1c6;font-size:13px}
  #bar .install{background:#8ab4f8;color:#202124;border:0;border-radius:16px;padding:7px 14px;font-weight:600}
  .app{padding:72px 28px 28px}
  .side{position:fixed;left:0;top:48px;bottom:0;width:64px;background:#152032;border-right:1px solid #243247}
  .main{margin-left:64px}
  h1{margin:0 0 8px;font-size:28px}
  .muted{color:#9fb0c3;margin:0 0 20px}
  .card{background:#1a2433;border:1px solid #2a3a4d;border-radius:12px;padding:18px;max-width:520px}
  #dlg{position:fixed;inset:0;z-index:20;background:rgba(0,0,0,.45);display:none;align-items:center;justify-content:center}
  #dlg .box{width:420px;background:#fff;color:#202124;border-radius:12px;padding:20px 22px 16px;
    box-shadow:0 12px 40px rgba(0,0,0,.35)}
  #dlg h2{margin:0 0 8px;font-size:1.15rem}
  #dlg p{margin:0 0 16px;color:#5f6368;font-size:14px}
  #dlg .row{display:flex;justify-content:flex-end;gap:8px}
  #dlg button{border:0;border-radius:18px;padding:8px 16px;font-weight:600}
  #dlg .cancel{background:transparent;color:#1a73e8}
  #dlg .ok{background:#1a73e8;color:#fff}
</style></head><body>
<div id="bar">
  <span>☰</span><span style="font-size:13px">Nika CRM</span>
  <div class="url">https://service.nika-crm.ru/</div>
  <button type="button" class="install" id="btn">Установить</button>
</div>
<div class="side"></div>
<div class="app main">
  <h1>Nika CRM</h1>
  <p class="muted">Демо · заявки, склад, касса</p>
  <div class="card">Откройте CRM по HTTPS → в Chrome/Edge нажмите <b>Установить</b> в адресной строке (или меню ⋮ → «Установить приложение…»).</div>
</div>
<div id="dlg"><div class="box" role="dialog">
  <h2>Установить приложение?</h2>
  <p>Nika CRM · service.nika-crm.ru<br>Ярлык на рабочем столе и в меню «Пуск». После установки можно закрепить на панели задач Windows.</p>
  <div class="row">
    <button type="button" class="cancel" id="cancel">Отмена</button>
    <button type="button" class="ok">Установить</button>
  </div>
</div></div>
<script>
  btn.onclick = () => { dlg.style.display = 'flex'; };
  cancel.onclick = () => { dlg.style.display = 'none'; };
</script>
</body></html>
            """
        )
        page.wait_for_timeout(200)
        page.screenshot(path=str(out / "42-pwa-chrome-install.png"), full_page=False)
        print("saved", out / "42-pwa-chrome-install.png")
        page.click("#btn")
        page.wait_for_timeout(250)
        page.screenshot(path=str(out / "43-pwa-chrome-dialog.png"), full_page=False)
        print("saved", out / "43-pwa-chrome-dialog.png")
        context.close()

        # 44 taskbar
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="ru-RU")
        page = context.new_page()
        page.set_content(
            """
<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>
  html,body{margin:0;height:100%;background:#1a2332;font-family:Segoe UI,system-ui,sans-serif;color:#e8eef7}
  .desk{position:relative;height:100%;background:linear-gradient(160deg,#243447,#1a2332 55%,#121820)}
  .win{position:absolute;left:12%;top:10%;width:70%;height:62%;background:#0f1720;border:1px solid #3a4a5c;border-radius:10px;overflow:hidden;box-shadow:0 18px 50px rgba(0,0,0,.45)}
  .title{height:36px;background:#1c2836;display:flex;align-items:center;padding:0 12px;gap:8px;font-size:13px}
  .dot{width:10px;height:10px;border-radius:50%;background:#6b7c90}
  .body{padding:28px 32px;font-size:22px;font-weight:700}
  .sub{margin-top:8px;font-size:14px;font-weight:400;color:#9fb0c3}
  .task{position:absolute;left:0;right:0;bottom:0;height:48px;background:rgba(16,22,30,.92);display:flex;align-items:center;gap:10px;padding:0 14px;border-top:1px solid #2c3a4a}
  .ico{width:36px;height:36px;border-radius:8px;background:#2563eb;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px}
  .ico.active{outline:2px solid #8ab4f8;outline-offset:2px}
  .pin{margin-left:8px;font-size:12px;color:#b7c6d8;background:#243244;padding:6px 10px;border-radius:8px}
</style></head><body>
<div class="desk">
  <div class="win">
    <div class="title"><span class="dot"></span><span class="dot"></span><span class="dot"></span><span>Nika CRM</span></div>
    <div class="body">Nika CRM<div class="sub">Установленное PWA-приложение (режим standalone)</div></div>
  </div>
  <div class="task">
    <div class="ico">⊞</div>
    <div class="ico active" title="Nika CRM">N</div>
    <div class="pin">ПКМ по иконке → «Закрепить на панели задач»</div>
  </div>
</div>
</body></html>
            """
        )
        page.wait_for_timeout(200)
        page.screenshot(path=str(out / "44-pwa-windows-taskbar.png"), full_page=False)
        print("saved", out / "44-pwa-windows-taskbar.png")
        context.close()

        # 45 mobile
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
            locale="ru-RU",
        )
        mpage = mobile.new_page()
        mpage.set_content(
            """
<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  html,body{margin:0;background:#0b1220;color:#e8eef7;font-family:system-ui,-apple-system,sans-serif}
  .phone{min-height:100vh;display:flex;flex-direction:column}
  .urlbar{margin:10px 12px;background:#1a2433;border-radius:12px;padding:10px 12px;font-size:13px;color:#9fb0c3}
  .sheet{margin-top:auto;background:#152032;border-radius:18px 18px 0 0;padding:18px 16px 28px;box-shadow:0 -8px 30px rgba(0,0,0,.35)}
  .sheet h1{margin:0 0 6px;font-size:17px}
  .sheet p{margin:0 0 14px;color:#9fb0c3;font-size:13px}
  .row{display:flex;align-items:center;gap:12px;padding:12px 8px;border-top:1px solid #243247;font-size:15px}
  .ico{width:28px;height:28px;border-radius:7px;background:#2563eb;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px}
  .hl{background:#1e3350;border-radius:10px}
</style></head><body>
<div class="phone">
  <div class="urlbar">service.nika-crm.ru</div>
  <div style="flex:1;padding:24px 16px;font-size:22px;font-weight:700">Nika CRM</div>
  <div class="sheet">
    <h1>Поделиться</h1>
    <p>Chrome / Safari на телефоне</p>
    <div class="row"><span>⧉</span> Копировать ссылку</div>
    <div class="row hl"><span class="ico">＋</span> На экран «Домой»</div>
    <div class="row"><span>☆</span> Добавить в избранное</div>
  </div>
</div>
</body></html>
            """
        )
        mpage.wait_for_timeout(200)
        mpage.screenshot(path=str(out / "45-pwa-mobile-add-home.png"), full_page=False)
        print("saved", out / "45-pwa-mobile-add-home.png")
        mobile.close()
        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
