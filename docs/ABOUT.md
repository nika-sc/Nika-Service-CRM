# О проекте и установка

**Nika CRM** — бесплатная open-source CRM для сервисных центров: заявки на ремонт, склад, касса, зарплата, отчёты и портал клиента.

Работает на своём сервере или в локальной сети, без SaaS.

- Живое демо: [demo.nika-sc.ru](https://demo.nika-sc.ru/)
- Исходный код: [GitHub Nika-Service-CRM](https://github.com/nika-sc/Nika-Service-CRM)
- Лицензия: MIT

Автор: **Александр Смелков**, сервисный центр «Ника», Сочи.

## Что умеет система

- Заявки: реестр, канбан, журнал, услуги/товары/оплаты, закрепление (📌)
- Клиенты и устройства, клиентский портал
- Склад и закупки, магазин
- **Счета B2B** для ИП и юрлиц: печать счёта/акта/накладной (в т.ч. бланк без подписи/печати под живое проставление), оплата с заявкой или через магазин
- Касса и зарплата (начисления при закрытии, выплаты)
- Отчёты: сводный, сводка дня, касса
- Чат сотрудников, email-уведомления

Подробно по экранам: [руководство](/docs/guide) и [сценарий рабочего дня](/docs/walkthrough).

## Быстрый старт без длинной инструкции

| Путь | Когда выбирать |
|------|----------------|
| **[Бесплатная установка на VPS](#free-install-vps)** | Купили сервер у FirstVDS по рефералу — автор поставит CRM и поддержит |
| **[Windows SETUP](#windows-setup-offline)** | Нужен свой ПК Windows 10/11, без Linux |
| **Самостоятельно** | Docker / Ubuntu / локальная разработка — разделы ниже |

## Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/nika-sc/Nika-Service-CRM.git
cd Nika-Service-CRM
```

### 2. Windows (офлайн SETUP)

Для Windows 10/11 x64 доступен автономный установщик с PostgreSQL и службой автозапуска.  
Ссылки на скачивание — на [главной демо](/) (блок Windows SETUP) и в [релизе GitHub](https://github.com/nika-sc/Nika-Service-CRM/releases).

После установки демо-логины (пароль `111111`): `admin`, `manager`, `master`, `viewer`.

### 3. Linux / VPS (Ubuntu)

One-shot установка: [`scripts/linux_setup.sh`](https://github.com/nika-sc/Nika-Service-CRM/blob/main/scripts/linux_setup.sh) (клон → PostgreSQL → bootstrap-дамп → systemd `nikacrm`).  
Обновление без потери данных: [`scripts/linux_upgrade.sh`](https://github.com/nika-sc/Nika-Service-CRM/blob/main/scripts/linux_upgrade.sh) — **не** используйте `linux_setup` для апгрейда.  
Подробности: корневой [README](https://github.com/nika-sc/Nika-Service-CRM/blob/main/README.md) (раздел VPS) и [docs/DEPLOY.md](DEPLOY.md).

### 4. Docker

```bash
cp docker/env.example .env
# задайте SECRET_KEY и параметры Postgres
docker compose up -d --build
```

Подробности: каталог [`docker/`](https://github.com/nika-sc/Nika-Service-CRM/tree/main/docker) в репозитории.

### 5. Локально (разработчикам)

Нужны Python 3.10+, PostgreSQL, зависимости из `requirements.txt`, файл `.env` с `DB_DRIVER=postgres` и `DATABASE_URL`.  
Запуск: `python run.py` → обычно `http://127.0.0.1:5000`.

Санитизированный bootstrap-дамп: [`database/bootstrap/`](https://github.com/nika-sc/Nika-Service-CRM/tree/main/database/bootstrap).

## Помощь и бесплатная установка

- Баги и идеи: `nika-sc@bk.ru` (тема `Nika-CRM`)
- **Бесплатная установка/поддержка** при покупке VPS у FirstVDS по [рефералу](https://firstvds.ru/?from=528402) и промокоду **`648528402`**: `nika-sc@bk.ru` (тема `Nika-CRM Помощь по установке`)
- Telegram: [t.me/nikaserviceadler](https://t.me/nikaserviceadler)
