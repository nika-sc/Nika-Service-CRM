# Скриншоты для USER_WALKTHROUGH.md

Реальные PNG с демо/локальной CRM (имена как в `USER_WALKTHROUGH.md`):

`01-login.png` … `23-staff-chat.png`

Автосъёмка:

```powershell
.\.venv-win\Scripts\pip.exe install playwright
.\.venv-win\Scripts\playwright.exe install chromium

# Демо
.\.venv-win\Scripts\python.exe scripts\capture_walkthrough_screenshots.py --base-url https://demo.nika-sc.ru --user demo_admin --password Demo2026!

# Локально
.\.venv-win\Scripts\python.exe scripts\capture_walkthrough_screenshots.py --base-url http://127.0.0.1:5000 --user admin --password 111111
```
