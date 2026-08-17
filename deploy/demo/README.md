# Автообновление демо-VPS с публичного репозитория

Демо клонируется с **https://github.com/nika-sc/Nika-Service-CRM** (ветка **`main`**). Ниже — автоматическое подтягивание кода при **перезагрузке** и при **новых коммитах** на GitHub.

## Что ставится на сервер

1. **`nikacrm-demo-sync.sh`** — режимы:
   - **`boot`**: `git fetch` + `git merge --ff-only` (ошибки сети не блокируют старт), затем `pip install -r requirements.txt` в `venv`.
   - **`poll`**: то же при расхождении с `origin/main`, затем `systemctl restart nikacrm`.
2. **`nikacrm-demo-sync-onboot.service`** — однократно при загрузке (до `nikacrm`).
3. **`nikacrm-demo-sync-poll.timer`** — опрос GitHub каждые 5 минут (первый запуск через 3 минуты после boot).
4. **Drop-in для `nikacrm.service`** — чтобы gunicorn стартовал после git-pull.

Опционально: workflow в публичном репо (файл `github-workflows/demo-vps-deploy-on-push.yml.example`) — деплой **сразу** после `push` в `main` по SSH (секреты в GitHub Actions).

## Установка (один раз, на демо-сервере под root)

Пути по умолчанию: каталог приложения `/root/Nika-Service-CRM`, сервис `nikacrm`. При другом пути создайте `/etc/default/nikacrm-demo-sync` по образцу `etc-default-nikacrm-demo-sync.example`.

```bash
cd /root/Nika-Service-CRM
git pull origin main

sudo install -m 0755 deploy/demo/nikacrm-demo-sync.sh /usr/local/sbin/nikacrm-demo-sync.sh

sudo cp deploy/demo/systemd/nikacrm-demo-sync-onboot.service /etc/systemd/system/
sudo cp deploy/demo/systemd/nikacrm-demo-sync-poll.service /etc/systemd/system/
sudo cp deploy/demo/systemd/nikacrm-demo-sync-poll.timer /etc/systemd/system/

sudo mkdir -p /etc/systemd/system/nikacrm.service.d
sudo cp deploy/demo/systemd/nikacrm.service.d-demo-sync.conf /etc/systemd/system/nikacrm.service.d/demo-sync.conf

sudo systemctl daemon-reload
sudo systemctl enable nikacrm-demo-sync-onboot.service
sudo systemctl enable --now nikacrm-demo-sync-poll.timer
sudo systemctl restart nikacrm
```

Проверка:

```bash
systemctl list-timers | grep nikacrm-demo
/usr/local/sbin/nikacrm-demo-sync.sh poll
```

## Публичный репозиторий: мгновенный деплой по push

1. Скопируйте `deploy/demo/github-workflows/demo-vps-deploy-on-push.yml.example` в репозиторий **Nika-Service-CRM** как `.github/workflows/demo-vps-deploy.yml`.
2. В GitHub → **Settings → Secrets and variables → Actions** добавьте `DEMO_VPS_HOST` и `DEMO_VPS_SSH_KEY`.
3. На сервере должен быть установлен скрипт `/usr/local/sbin/nikacrm-demo-sync.sh` (как выше).

Таймер можно оставить как резерв (ручные push без Actions, сбои сети).

## Ежедневный бэкап данных на email

`scripts/backup_and_email.sh` кладёт в архив **только то, чего нет в git**: PostgreSQL (`pg_dump -Fc`), `.env`, загрузки, nginx/Let’s Encrypt. Исходники (`app/`, `templates/`, скриншоты гайда, `static/cdn`) **не** входят — они уже на GitHub.

На DEMO Service+Fitness+хаб ночной снимок — отдельный скрипт на хаб-VPS (`dr_snapshot_nika_crm_ru.sh`): два письма (Service-демо и Fitness+хаб), тоже без исходников.

Для self-hosted (systemd + host Postgres), если нужны доп. файлы:

```bash
cd /root/Nika-Service-CRM
BACKUP_MODE=host BACKUP_XZ_OPTS="-3 -T1" \
  /bin/bash scripts/backup_and_email.sh smelkov2008@yandex.ru
```

Архивы: `data/database/backups/auto/`. Лог: `data/logs/backup_email.log`. Хранение ~14 дней.

На малом VPS (~1 ГБ RAM) не использовать `xz -9e` — скрипт сам снижает уровень при малой памяти; для DEMO явно `BACKUP_XZ_OPTS="-3 -T1"`.

## Замечания

- На демо не должно быть локальных коммитов: только fast-forward с `origin/main`.
- Удалённый `origin` должен указывать на публичный HTTPS URL репозитория (без интерактивного логина).
- После `git pull` скрипт бэкапа должен оставаться актуальной версией из `main` (режим host).