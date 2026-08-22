"""Публичный блог на SEO-лендинге (PUBLIC_LANDING): история фич CRM."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from flask import Blueprint, abort, g, redirect, render_template, url_for

from app.routes.main import _landing_canonical_url, _public_landing_enabled, _windows_setup_info
from app.utils.public_markdown import render_docs_markdown

bp = Blueprint("public_blog", __name__)
logger = logging.getLogger(__name__)

# Новые сверху; slug = имя файла без .md (без числового префикса в URL)
# date — дата и время публикации (МСК), формат для списка: «2026-08-09 17:45»
_POSTS = [
    {
        "slug": "security-catalog-invoices",
        "file": "blog/36-security-catalog-invoices.md",
        "date": "2026-08-22 11:30",
        "title": "Безопасность и быстрее разделы — Nika Service CRM",
        "description": (
            "22 августа 2026: обновили систему безопасности и ускорили заявку, "
            "клиентов, склад и настройки; в диагностике — готовые шаблоны текста."
        ),
        "heading": "Безопасность и скорость",
        "teaser": "Обновили безопасность и ускорили основные разделы CRM.",
    },
    {
        "slug": "diagnostics-templates-perf",
        "file": "blog/35-diagnostics-templates-perf.md",
        "date": "2026-08-20 22:20",
        "title": "Шаблоны диагностики и быстрее разделы CRM — Nika Service CRM",
        "description": (
            "20 августа 2026: готовые тексты диагностики по типу и модели устройства; "
            "карточка заявки, клиенты, склад и настройки открываются быстрее."
        ),
        "heading": "Шаблоны диагностики",
        "teaser": "Готовый текст диагностики и быстрее заявка, клиенты, склад.",
    },
    {
        "slug": "shop-master-required",
        "file": "blog/34-shop-master-required.md",
        "date": "2026-08-19 22:25",
        "title": "В магазине обязателен мастер — Nika Service CRM",
        "description": (
            "19 августа 2026: продажу в магазине нельзя провести без мастера; "
            "без исполнителя зарплата не начисляется, система показывает предупреждение."
        ),
        "heading": "Магазин: мастер обязателен",
        "teaser": "Без мастера чек в магазине не проводится — зарплата не теряется.",
    },
    {
        "slug": "diagnostics-uploads-persist",
        "file": "blog/33-diagnostics-uploads-persist.md",
        "date": "2026-08-17 16:55",
        "title": "Фото диагностики сохраняются после обновления сервера — Nika Service CRM",
        "description": (
            "17 августа 2026: снимки из окна диагностики пишутся на постоянный диск "
            "и остаются после обновления CRM; в кабинете клиента они тоже открываются."
        ),
        "heading": "Фото диагностики на диске",
        "teaser": "Снимки диагностики больше не пропадают после обновления сервера.",
    },
    {
        "slug": "all-orders-default-in-progress",
        "file": "blog/32-all-orders-default-in-progress.md",
        "date": "2026-08-17 16:45",
        "title": "Список заявок сразу открывается «Все в работе» — Nika Service CRM",
        "description": (
            "17 августа 2026: раздел Заявки по умолчанию показывает фильтр «Все в работе», "
            "а не весь архив. Полный список — по бейджу «Все»."
        ),
        "heading": "Заявки: сразу «Все в работе»",
        "teaser": "Меню Заявки открывает живые заказы; полный реестр — бейдж «Все».",
    },
    {
        "slug": "receipt-print-guides",
        "file": "blog/31-receipt-print-guides.md",
        "date": "2026-08-16 22:50",
        "title": "Квитанция при приёмке и где читать руководство — Nika Service CRM",
        "description": (
            "16 августа 2026: квитанция сразу после новой заявки, пустая предварительная "
            "стоимость не печатается; ссылки на руководство пользователя и серию 1."
        ),
        "heading": "Квитанция и руководство",
        "teaser": "Печать при приёмке, карта гайда и новые функции ядра СЦ.",
    },
    {
        "slug": "shop-popular-checkout",
        "file": "blog/30-shop-popular-checkout.md",
        "date": "2026-08-16 16:45",
        "title": "Быстрая продажа в магазине: частые позиции и чек — Nika Service CRM",
        "description": (
            "16 августа 2026: в магазине сверху частые услуги и товары, продажа на одном экране, "
            "после проведения сразу печатается товарный чек."
        ),
        "heading": "Быстрая продажа в магазине",
        "teaser": "Частые клише и оснастка в один клик; чек и оплата на одном экране.",
    },
    {
        "slug": "one-time-cogs-portal-catalog",
        "file": "blog/29-one-time-cogs-portal-catalog.md",
        "date": "2026-08-16 13:30",
        "title": "Разовая себестоимость, справочники и кабинет клиента — Nika Service CRM",
        "description": (
            "16 августа 2026: себестоимость разового товара и услуги в кассе и отчётах, "
            "справочники по популярности и связям, в кабинете — история ремонта и профиль."
        ),
        "heading": "Разовая себестоимость и кабинет",
        "teaser": "Себ. разовых позиций в кассе; тип→марка→модель; история ремонта в ЛК.",
    },
    {
        "slug": "diagnostics-chat-toasts",
        "file": "blog/28-diagnostics-chat-toasts.md",
        "date": "2026-08-15 21:15",
        "title": "Диагностика заявки, кабинет клиента и чат в меню — Nika Service CRM",
        "description": (
            "15 августа 2026: текст диагностики до закрытия заявки, в кабинете клиента — "
            "диагностика с фото, печать чека, устройства с заявками и история платежей."
        ),
        "heading": "Диагностика, кабинет и чат",
        "teaser": "Диагностика до «Готов/Закрыт», в ЛК — фото, чек, устройства и платежи.",
    },
    {
        "slug": "security-session-files",
        "file": "blog/27-security-session-files.md",
        "date": "2026-08-15 21:00",
        "title": "Вход, сессии и файлы заявок — Nika Service CRM",
        "description": (
            "15 августа 2026: понятные сообщения при лимите входа, повторный вход после простоя, "
            "файлы диагностики и кабинета только своим заявкам."
        ),
        "heading": "Вход, сессии и файлы",
        "teaser": "Лимит входа ≠ блокировка учётки; простой сессии; фото диагностики и кабинет.",
    },
    {
        "slug": "security-hardening",
        "file": "blog/26-security-hardening.md",
        "date": "2026-08-14 12:30",
        "title": "Усиление входа и паролей личного кабинета — Nika Service CRM",
        "description": (
            "14 августа 2026: общий lockout по Redis, ссылка задать пароль в письме, "
            "пароль ЛК не хранится открытым текстом, TRUSTED_HOSTS обязателен в production."
        ),
        "heading": "Усиление входа и паролей ЛК",
        "teaser": "Lockout на Redis, ссылка /portal/set-password, пароль кабинета только хеш.",
    },
    {
        "slug": "pwa-install-taskbar",
        "file": "blog/25-pwa-install-taskbar.md",
        "date": "2026-08-09 18:15",
        "title": "Установка PWA и закрепление на панели задач Windows — Nika CRM",
        "description": (
            "9 августа 2026: как установить Nika CRM как PWA в Chrome/Edge, закрепить "
            "на панели задач Windows и добавить на главный экран телефона."
        ),
        "heading": "PWA: установка и панель задач",
        "teaser": "Chrome/Edge → Установить → закрепить на панели задач; мобильный — «На экран Домой».",
    },
    {
        "slug": "windows-setup-1-0-6",
        "file": "blog/24-windows-setup-1-0-6.md",
        "date": "2026-08-09 17:45",
        "title": "Windows SETUP 1.0.6 (2026-08-09): LAN, SMTP и перезапуск службы — Nika CRM",
        "description": (
            "9 августа 2026: офлайн-установщик 1.0.6 — LAN, SMTP без noreply@example.com, "
            "после сохранения почты перезапуск службы, плейсхолдеры «От кого», квитанции."
        ),
        "heading": "Windows SETUP 1.0.6",
        "teaser": "Сборка 2026-08-09: LAN + SMTP + рестарт службы после сохранения почты.",
    },
    {
        "slug": "smtp-mail-setup",
        "file": "blog/22-smtp-mail-setup.md",
        "date": "2026-08-08 18:30",
        "title": "Настройка почты SMTP: Mail.ru и поле «От кого» — Nika CRM",
        "description": (
            "8 августа 2026: как заполнить SMTP в настройках CRM, почему Mail.ru отклоняет "
            "noreply@example.com и чем логин отличается от поля «От кого»."
        ),
        "heading": "Настройка почты (SMTP)",
        "teaser": "Mail.ru/Яндекс: «От кого» = логин; демо noreply@example.com ломает отправку.",
    },
    {
        "slug": "lan-access-and-receipt-fixes",
        "file": "blog/21-lan-access-and-receipt-fixes.md",
        "date": "2026-08-08 16:00",
        "title": "LAN, квитанция и предварительная стоимость — Nika CRM",
        "description": (
            "8 августа 2026: доступ CRM из локальной сети, объединение внешнего вида и комплектации "
            "в квитанции, сохранение размера шрифта в шаблонах, поле предварительной стоимости."
        ),
        "heading": "LAN, квитанция и предварительная стоимость",
        "teaser": "Доступ по сети, одна строка в квитанции, font-size в шаблонах, оценка цены при приёмке.",
    },
    {
        "slug": "customer-portal-login",
        "file": "blog/20-customer-portal-login.md",
        "date": "2026-08-08 12:00",
        "title": "Клиентский портал: вход, доступ и работа — Nika CRM",
        "description": (
            "8 августа 2026: отдельный сценарий личного кабинета клиента — адрес входа, "
            "выдача пароля в CRM и разделы портала со скриншотами."
        ),
        "heading": "Клиентский портал: вход и работа",
        "teaser": "Как сотруднику выдать доступ, а клиенту войти в /portal/login и пользоваться кабинетом.",
    },
    {
        "slug": "salary-499-abort",
        "file": "blog/19-salary-499-abort.md",
        "date": "2026-08-05 19:00",
        "title": "Багфикс: меньше nginx 499 на Зарплате — Nika CRM",
        "description": (
            "5 августа 2026: AbortController для запросов ЗП, больше слотов gunicorn на WORK, "
            "request_time в nginx-логе для диагностики 499."
        ),
        "heading": "Меньше 499 на Зарплате",
        "teaser": "Отмена устаревших fetch + ёмкость воркеров + тайминги в access-логе.",
    },
    {
        "slug": "all-orders-light",
        "file": "blog/18-all-orders-light.md",
        "date": "2026-08-05 17:30",
        "title": "Багфикс: лёгкий реестр заявок /all_orders — Nika CRM",
        "description": (
            "5 августа 2026: меню статусов и контакты не дублируются в каждой строке DataTables; "
            "канбан без мёртвых data-* и лишнего запроса."
        ),
        "heading": "Лёгкий реестр заявок",
        "teaser": "AJAX реестра ~271→82 КБ; канбан легче и быстрее.",
    },
    {
        "slug": "salary-reports-speed",
        "file": "blog/17-salary-reports-speed.md",
        "date": "2026-08-05 16:00",
        "title": "Багфикс: быстрее Зарплата и Отчёты — Nika CRM",
        "description": (
            "5 августа 2026: лёгкие итоги ЗП без полного отчёта, отдельный /api/salary/extras, "
            "продажи и клиенты в отчётах — SQL LIMIT и агрегаты по периоду."
        ),
        "heading": "Быстрее Зарплата и Отчёты",
        "teaser": "Без повторного полного отчёта ЗП и без загрузки всех продаж года в Python.",
    },
    {
        "slug": "client-detail-reports-size",
        "file": "blog/16-client-detail-reports-size.md",
        "date": "2026-08-05 14:30",
        "title": "Багфикс: лёгкая карточка клиента и отчёты без мегабайт HTML — Nika CRM",
        "description": (
            "5 августа 2026: карточка клиента без SSR тысяч option справочников; "
            "отчёты продаж/клиентов ограничивают таблицу, сохраняя полные итоги."
        ),
        "heading": "Клиенты и отчёты без тяжёлого HTML",
        "teaser": "Карточка клиента ~1.5 МБ → лёгкая; продажи/клиенты в отчётах — лимит строк.",
    },
    {
        "slug": "nav-hang-settings",
        "file": "blog/15-nav-hang-settings.md",
        "date": "2026-08-05 13:00",
        "title": "Багфикс: меню больше не зависает при быстрых переходах — Nika CRM",
        "description": (
            "5 августа 2026: настройки без SSR тысяч справочников устройств (~8 МБ → ~0.5 МБ), "
            "service worker network-first для HTML — быстрые клики по меню снова работают."
        ),
        "heading": "Багфикс зависания меню",
        "teaser": "Настройки похудели в разы; HTML больше не кэшируется SW — переходы не залипают.",
    },
    {
        "slug": "perf-salary-cash-settings",
        "file": "blog/14-perf-salary-cash-settings.md",
        "date": "2026-08-05 11:30",
        "title": "Быстрее Касса, Отчёты, Зарплата и Настройки — Nika CRM",
        "description": (
            "5 августа 2026: лёгкий первый запрос зарплаты, кэш сводки кассы, "
            "быстрее дашборд отчётов и настройки без загрузки всей таблицы parts."
        ),
        "heading": "Ускорение Кассы, Отчётов, ЗП и Настроек",
        "teaser": "Меньше тяжёлых запросов при открытии разделов — быстрее первый экран.",
    },
    {
        "slug": "salary-refund-split",
        "file": "blog/13-salary-refund-split.md",
        "date": "2026-08-05 10:00",
        "title": "Зарплата и возвраты: без двойных строк в карточке сотрудника — Nika CRM",
        "description": (
            "5 августа 2026: разбивка начислений по оплатам больше не учитывает "
            "полностью возвращённые платежи — без «двойных» строк в /salary."
        ),
        "heading": "Зарплата и возвраты оплат",
        "teaser": "Возвраты не дробят ЗП; закрытие из реестра больше не открывает оплату дважды.",
    },
    {
        "slug": "bugfixes-cache-salary",
        "file": "blog/12-bugfixes-cache-salary.md",
        "date": "2026-08-05 09:00",
        "title": "Багфиксы: Redis-кэш, дашборд и смена мастера с зарплатой — Nika CRM",
        "description": (
            "5 августа 2026: кнопка «Сменить исполнителей» на закрытой заявке с переносом ЗП; "
            "фиксы Redis (500 на услугах, type-drift дашборда)."
        ),
        "heading": "Смена исполнителей и багфиксы кэша",
        "teaser": "Закрытая заявка: смена мастера/менеджера с переносом ЗП. Плюс фиксы Redis.",
    },
    {
        "slug": "perf-cash-mobile",
        "file": "blog/11-perf-cash-mobile.md",
        "date": "2026-07-26 18:00",
        "title": "Производительность, касса по статьям и мобильное меню — Nika CRM",
        "description": (
            "Redis и gunicorn multi-worker, исправление периода «Прошлый месяц», "
            "итоги кассы по статьям и выезжающее меню на телефоне."
        ),
        "heading": "Скорость, касса, мобильное меню",
        "teaser": "Быстрее реестр, Обед за месяц в кассе, гамбургер-меню на мобиле.",
    },
    {
        "slug": "invoices-blank-signs",
        "file": "blog/10-invoices-blank-signs.md",
        "date": "2026-07-29 16:00",
        "title": "Печать счетов без подписи и печати — живая печать — Nika CRM",
        "description": (
            "Бланк счёта, акта и накладной без электронных картинок подписи и печати "
            "для проставления живых штампов; переключатель на карточке и в предпросмотре."
        ),
        "heading": "Печать без подписи и печати",
        "teaser": "Кнопка «жив.» — бланк под настоящую подпись и круглую печать.",
    },
    {
        "slug": "invoices-print-ux",
        "file": "blog/09-invoices-print-ux.md",
        "date": "2026-07-28 15:00",
        "title": "Счета B2B: печать, шаблоны и оплата без заявки — Nika CRM",
        "description": (
            "TinyMCE-шаблоны счёта, акта и накладной, печать A4, размеры подписи/печати, "
            "оплата без заявки в магазин и поиск телефонов 8/7/+7."
        ),
        "heading": "Счета: шаблоны печати и оплата",
        "teaser": "Редактор бланков и A4. Живая печать без картинок — в следующем посте.",
    },
    {
        "slug": "invoices-b2b",
        "file": "blog/08-invoices-b2b.md",
        "date": "2026-07-27 14:00",
        "title": "Счета для юрлиц и ИП — Nika CRM",
        "description": (
            "Модуль счетов B2B: выставление из заявки, печать счёта/акта/накладной, "
            "оплата переводом и связь с закрытием заявки."
        ),
        "heading": "Счета для юрлиц и ИП",
        "teaser": "Реестр счетов и базовый сценарий B2B. Обновление печати — в следующем посте.",
    },
    {
        "slug": "windows-landing-setup",
        "file": "blog/07-windows-landing-setup.md",
        "date": "2026-07-25 12:00",
        "title": "Windows SETUP, лендинг и установка на VPS — Nika CRM",
        "description": "Офлайн SETUP для Windows, SEO-лендинг демо и one-shot установка на Ubuntu.",
        "heading": "Windows SETUP, лендинг и VPS",
        "teaser": "Поставить CRM проще: Windows SETUP, публичный лендинг, linux_setup / linux_upgrade.",
    },
    {
        "slug": "navbar-mobile",
        "file": "blog/05-navbar-mobile.md",
        "date": "2026-05-20 12:00",
        "title": "Навбар и мобильный интерфейс — Nika CRM",
        "description": "Главное меню с подменю и удобная работа CRM на телефоне.",
        "heading": "Навбар и мобильный UI",
        "teaser": "Единое меню разделов и адаптация под узкий экран.",
    },
    {
        "slug": "oss-demo-docs",
        "file": "blog/06-oss-demo-docs.md",
        "date": "2026-04-15 12:00",
        "title": "Open Source, демо и документация на сайте — Nika CRM",
        "description": "Публичный репозиторий, демо-VPS и руководства на /docs без GitHub.",
        "heading": "OSS, демо и документация",
        "teaser": "Живое демо, автообновление с main и встроенные руководства.",
    },
    {
        "slug": "staff-chat-pins-security",
        "file": "blog/04-staff-chat-pins-security.md",
        "date": "2026-04-10 12:00",
        "title": "Чат сотрудников, pins и безопасность — Nika CRM",
        "description": "Внутренний чат с Push, закрепление заявок и hardening nginx/auth.",
        "heading": "Чат, pins, безопасность",
        "teaser": "Чат в сайдбаре, Web Push, pins в реестре, защита от сканеров.",
    },
    {
        "slug": "postgresql-production",
        "file": "blog/03-postgresql-production.md",
        "date": "2026-03-15 12:00",
        "title": "PostgreSQL и продакшен — Nika CRM",
        "description": "Только PostgreSQL: миграции, bootstrap-дамп, бэкапы и Docker.",
        "heading": "PostgreSQL и продакшен",
        "teaser": "Рабочая БД — Postgres; SQLite не для новых установок.",
    },
    {
        "slug": "rbac-reports-salary",
        "file": "blog/02-rbac-reports-salary.md",
        "date": "2026-01-20 12:00",
        "title": "Права, отчёты и зарплата — Nika CRM",
        "description": "RBAC, отчёты руководителя и начисление зарплаты по заявкам.",
        "heading": "Права, отчёты, зарплата",
        "teaser": "Роли, сводные отчёты и ЗП после полной оплаты.",
    },
    {
        "slug": "core-orders-warehouse-cash",
        "file": "blog/01-core-orders-warehouse-cash.md",
        "date": "2026-01-10 12:00",
        "title": "Заявки, склад и касса — ядро Nika Service CRM",
        "description": (
            "Серия 1: заявки, склад и касса плюс актуальные приёмка, магазин и кабинет. "
            "Ссылки на руководство пользователя и walkthrough."
        ),
        "heading": "Заявки, склад и касса",
        "teaser": "Ядро СЦ: приём, склад, касса; гайд и новые функции 2026.",
    },
]

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _require_public_landing():
    if not _public_landing_enabled():
        abort(404)


def _post_by_slug(slug: str) -> dict | None:
    for p in _POSTS:
        if p["slug"] == slug:
            return p
    return None


def _blog_ctx(heading: str, path: str, title: str, description: str, content_html=None, **extra) -> dict:
    canonical = _landing_canonical_url()
    page_url = f"{canonical}{path}"
    crumbs = [
        {"name": "Главная", "item": f"{canonical}/"},
        {"name": "Блог", "item": f"{canonical}/blog"},
    ]
    if path != "/blog":
        crumbs.append({"name": heading, "item": page_url})
    return {
        "canonical_url": canonical,
        "page_url": page_url,
        "page_path": path,
        "page_title": title,
        "page_description": description,
        "page_heading": heading,
        "active_docs_nav": "blog",
        "content_html": content_html,
        "github_url": "https://github.com/nika-sc/Nika-Service-CRM",
        "windows_setup": _windows_setup_info(),
        "og_image_url": f"{canonical}{url_for('static', filename='marketing/og-landing.jpg')}",
        "breadcrumb_items": crumbs,
        "schema_type": "Blog" if path == "/blog" else "BlogPosting",
        **extra,
    }


@bp.before_request
def _mark_indexable():
    if _public_landing_enabled():
        g.allow_search_indexing = True


@bp.route("/blog")
def blog_index():
    _require_public_landing()
    posts = [
        {
            **p,
            "url": url_for("public_blog.blog_post", slug=p["slug"]),
        }
        for p in _POSTS
    ]
    return render_template(
        "marketing/blog/index.html",
        **_blog_ctx(
            "Блог Nika CRM",
            "/blog",
            "Блог Nika CRM — обновления и фичи для сервисных центров",
            "История возможностей бесплатной CRM: заявки, склад, касса, чат, демо, счета для юрлиц.",
            posts=posts,
        ),
    )


@bp.route("/blog/<slug>")
def blog_post(slug: str):
    _require_public_landing()
    if not _SLUG_RE.match(slug or ""):
        abort(404)
    # Старый пост 1.0.5 слит в 1.0.6
    if slug == "windows-setup-1-0-5":
        return redirect(url_for("public_blog.blog_post", slug="windows-setup-1-0-6"), code=301)
    post = _post_by_slug(slug)
    if not post:
        abort(404)
    try:
        html = render_docs_markdown(post["file"])
    except FileNotFoundError:
        logger.exception("Blog post missing: %s", post["file"])
        abort(404)
    return render_template(
        "marketing/blog/post.html",
        **_blog_ctx(
            post["heading"],
            f"/blog/{slug}",
            post["title"],
            post["description"],
            content_html=html,
            post=post,
        ),
    )


def blog_sitemap_paths() -> list[str]:
    """Пути для sitemap.xml."""
    paths = ["/blog"]
    paths.extend(f"/blog/{p['slug']}" for p in _POSTS)
    return paths
