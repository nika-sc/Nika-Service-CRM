## Windows Offline SETUP 1.0.10 (2026-10-23)

Автономный установщик Nika CRM для Windows 10/11 x64.

### Скачать

- [NikaCRM-Offline-Setup-1.0.10-x64.exe](https://github.com/nika-sc/Nika-Service-CRM/releases/download/windows-setup-1.0.10/NikaCRM-Offline-Setup-1.0.10-x64.exe)
- Зеркало: https://service.nika-crm.ru/downloads/NikaCRM-Offline-Setup-1.0.10-x64.exe

SHA256: `ED876CEFCE9F0C74912C4CDEC843CF4626FEF7B5B6845F50EF7C4D03C4432FA9` (сборка 2026-10-23, 394 МБ).

### Что исправлено

Установка 1.0.9 не проходила, если на компьютере уже был Python: в папке Nika CRM не появлялся `python.exe`. В 1.0.10 интерпретатор CRM лежит отдельно и не меняет уже установленный Python.

Удаление спрашивает, удалять ли базу. Резервная копия остаётся в `%ProgramData%\NikaCRM-backup`. Чужой Python и чужой PostgreSQL не удаляются.

Обновление поверх и сохранение базы — как в **1.0.8**: один EXE, Python и PostgreSQL внутри.

### Документация

- Руководство: https://service.nika-crm.ru/docs/guide (§ 2.3)
- Блог: https://service.nika-crm.ru/blog/windows-setup-1-0-10
