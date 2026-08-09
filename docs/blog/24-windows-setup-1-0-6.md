# Windows SETUP 1.0.6 (2026-08-09): перезапуск службы после SMTP

Дата сборки: **2026-08-09**. Версия установщика: **1.0.6**.

## Скачать

- [NikaCRM-Offline-Setup-1.0.6-x64.exe (GitHub)](https://github.com/nika-sc/Nika-Service-CRM/releases/download/windows-setup-1.0.6/NikaCRM-Offline-Setup-1.0.6-x64.exe)
- [Страница релиза `windows-setup-1.0.6`](https://github.com/nika-sc/Nika-Service-CRM/releases/tag/windows-setup-1.0.6)
- [Зеркало на демо](https://service.nika-crm.ru/downloads/NikaCRM-Offline-Setup-1.0.6-x64.exe)

SHA256: `FA029F7CC5B53AA2C7CFD39C13539280A6CD654AA0BB1674AD6394F8D0A67387`

## Что изменилось относительно 1.0.5

### Почта (SMTP) на Windows
- После **сохранения** настроек почты CRM показывает предупреждение: перезапустите службу ярлыком **«Nika CRM — Перезапуск службы»** на рабочем столе.
- Без рестарта служба может держать старые `MAIL_*` из `.env` — тест письма «как будто не сохранилось».
- В форме SMTP понятнее плейсхолдеры: `Название вашей компании <ваш@email.ru>` (email внутри `<>` = логин).
- Гайд: [USER_GUIDE § 13.5](/docs/guide#135-почта-smtp), [smtp-mail-setup](/blog/smtp-mail-setup).

### Уже в 1.0.5 (остаётся)
- Доступ из LAN, firewall.
- Демо-отправитель `noreply@example.com` не ломает Mail.ru.
- Правки квитанций и предварительной стоимости.

## После установки

1. Ярлык **Nika CRM — Открыть** → `http://127.0.0.1:5000`.
2. Настройки → Почта: заполните SMTP → **Сохранить**.
3. Ярлык **Nika CRM — Перезапуск службы** → повторите тест письма.
4. Смените демо-пароли (`111111`).
