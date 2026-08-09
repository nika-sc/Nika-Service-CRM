## Windows Offline SETUP 1.0.6 (2026-08-09)

Автономный установщик Nika CRM для Windows 10/11 x64.

### Скачать

- [NikaCRM-Offline-Setup-1.0.6-x64.exe](https://github.com/nika-sc/Nika-Service-CRM/releases/download/windows-setup-1.0.6/NikaCRM-Offline-Setup-1.0.6-x64.exe)
- Зеркало: https://service.nika-crm.ru/downloads/NikaCRM-Offline-Setup-1.0.6-x64.exe

SHA256: `FA029F7CC5B53AA2C7CFD39C13539280A6CD654AA0BB1674AD6394F8D0A67387`

### Важно: почта (SMTP)

1. **Настройки → Почта** — заполните SMTP и поле **От кого** как  
   `Название вашей компании <ваш@email.ru>` (email = логин).
2. Нажмите **Сохранить**.
3. Перезапустите службу ярлыком на рабочем столе **«Nika CRM — Перезапуск службы»**.
4. Повторите тест письма.

Без шага 3 служба Windows может ещё держать старые `MAIL_*` из `.env`.

### Документация

- Руководство: https://service.nika-crm.ru/docs/guide (§ 2.3 Windows, § 13.5 SMTP)
- Сценарий со скриншотами: https://service.nika-crm.ru/docs/walkthrough
- Блог: https://service.nika-crm.ru/blog/windows-setup-1-0-6
- SMTP FAQ: https://service.nika-crm.ru/blog/smtp-mail-setup

### Демо-логины после установки

Пароль для всех: `111111` — `admin`, `manager`, `master`, `viewer`. Смените перед реальной работой.
