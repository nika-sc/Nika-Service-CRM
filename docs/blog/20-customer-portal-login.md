# Клиентский портал: как выдать доступ и как входит клиент

8 августа 2026: обновили документацию по личному кабинету клиента, добавили отдельный сценарий входа и реальные скриншоты с демо.

## Адрес входа в портал

- Локальная установка: `http://127.0.0.1:5000/portal/login`
- Публичное демо: `https://demo.nika-sc.ru/portal/login`

Это отдельный вход от CRM сотрудников (`/login`).

![Вход в портал](assets/walkthrough/29-portal-login.png)

## Что делает сотрудник в CRM

1. Открывает список клиентов `/clients`.
2. Переходит в карточку клиента.
3. Выдаёт пароль для портала (или обновляет его) и передаёт клиенту телефон + временный пароль.

![Список клиентов](assets/walkthrough/30-portal-clients-list.png)

![Карточка клиента](assets/walkthrough/31-portal-client-card.png)

![Пароль портала задан](assets/walkthrough/32-portal-password-issued.png)

## Что делает клиент

1. Открывает `/portal/login`.
2. Вводит телефон и пароль.
3. При первом входе меняет пароль.
4. Попадает в личный кабинет.

![Форма входа заполнена](assets/walkthrough/33-portal-login-filled.png)

![Дашборд клиента](assets/walkthrough/34-portal-dashboard.png)

## Что видно в личном кабинете

- `Мои заявки` (`/portal/orders`)
- `Платежи` (`/portal/payments`)
- `Мои устройства` (`/portal/devices`)
- `Кошелёк` (`/portal/wallet`)

![Мои заявки](assets/walkthrough/35-portal-orders.png)

![Платежи](assets/walkthrough/36-portal-payments.png)

![Мои устройства](assets/walkthrough/37-portal-devices.png)

![Кошелёк](assets/walkthrough/38-portal-wallet.png)

## Где смотреть полное руководство

- Пошаговый сценарий: [USER_WALKTHROUGH.md](USER_WALKTHROUGH.md) (раздел про портал)
- Полный справочник: [USER_GUIDE.md](USER_GUIDE.md) (§ 17)
