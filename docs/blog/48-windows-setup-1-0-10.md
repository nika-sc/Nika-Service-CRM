# Windows SETUP 1.0.10: установка рядом с уже стоящим Python

Дата сборки: **2026-10-23**. Версия установщика: **1.0.10**.

## Скачать

- [NikaCRM-Offline-Setup-1.0.10-x64.exe (GitHub)](https://github.com/nika-sc/Nika-Service-CRM/releases/download/windows-setup-1.0.10/NikaCRM-Offline-Setup-1.0.10-x64.exe)
- [Страница релиза `windows-setup-1.0.10`](https://github.com/nika-sc/Nika-Service-CRM/releases/tag/windows-setup-1.0.10)
- [Зеркало на демо](https://service.nika-crm.ru/downloads/NikaCRM-Offline-Setup-1.0.10-x64.exe)

SHA256: `ED876CEFCE9F0C74912C4CDEC843CF4626FEF7B5B6845F50EF7C4D03C4432FA9` (сборка 2026-10-23, 394 МБ).

## Что починили

В 1.0.9 установка останавливалась, если на компьютере уже был Python 3.12: официальный установщик Python завершался сразу и не клал интерпретатор в папку Nika CRM.

В 1.0.10 у CRM свой Python. Он не записывается в «Программы и компоненты» и не меняет Python, который вы ставили сами. PostgreSQL по-прежнему ставится отдельно, своей службой.

Удаление спрашивает, стирать ли базу. Копия всё равно сохраняется в `%ProgramData%\NikaCRM-backup`. Чужой Python и чужой PostgreSQL при удалении не трогаются.

## Установка

Один EXE для Windows 10/11. Внутри Python и PostgreSQL. Новый установщик ставится **поверх** без потери базы. Если предыдущая попытка 1.0.9 оборвалась, сначала удалите Nika CRM в «Приложениях», затем ставьте 1.0.10.

Подробно: [руководство § 2.3](/docs/guide).
