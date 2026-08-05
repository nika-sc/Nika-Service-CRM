"""Публичный блог на SEO-лендинге (PUBLIC_LANDING): история фич CRM."""
from __future__ import annotations

import logging
import re
from pathlib import Path

from flask import Blueprint, abort, g, render_template, url_for

from app.routes.main import _landing_canonical_url, _public_landing_enabled, _windows_setup_info
from app.utils.public_markdown import render_docs_markdown

bp = Blueprint("public_blog", __name__)
logger = logging.getLogger(__name__)

# Новые сверху; slug = имя файла без .md (без числового префикса в URL)
_POSTS = [
    {
        "slug": "perf-salary-cash-settings",
        "file": "blog/14-perf-salary-cash-settings.md",
        "date": "2026-08",
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
        "date": "2026-08",
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
        "date": "2026-08",
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
        "date": "2026-07",
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
        "date": "2026-07",
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
        "date": "2026-07",
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
        "date": "2026-07",
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
        "date": "2026-07",
        "title": "Windows SETUP, лендинг и установка на VPS — Nika CRM",
        "description": "Офлайн SETUP для Windows, SEO-лендинг демо и one-shot установка на Ubuntu.",
        "heading": "Windows SETUP, лендинг и VPS",
        "teaser": "Поставить CRM проще: Windows SETUP, публичный лендинг, linux_setup / linux_upgrade.",
    },
    {
        "slug": "oss-demo-docs",
        "file": "blog/06-oss-demo-docs.md",
        "date": "2026-04",
        "title": "Open Source, демо и документация на сайте — Nika CRM",
        "description": "Публичный репозиторий, демо-VPS и руководства на /docs без GitHub.",
        "heading": "OSS, демо и документация",
        "teaser": "Живое демо, автообновление с main и встроенные руководства.",
    },
    {
        "slug": "navbar-mobile",
        "file": "blog/05-navbar-mobile.md",
        "date": "2026-05",
        "title": "Навбар и мобильный интерфейс — Nika CRM",
        "description": "Главное меню с подменю и удобная работа CRM на телефоне.",
        "heading": "Навбар и мобильный UI",
        "teaser": "Единое меню разделов и адаптация под узкий экран.",
    },
    {
        "slug": "staff-chat-pins-security",
        "file": "blog/04-staff-chat-pins-security.md",
        "date": "2026-04",
        "title": "Чат сотрудников, pins и безопасность — Nika CRM",
        "description": "Внутренний чат с Push, закрепление заявок и hardening nginx/auth.",
        "heading": "Чат, pins, безопасность",
        "teaser": "Чат в сайдбаре, Web Push, pins в реестре, защита от сканеров.",
    },
    {
        "slug": "postgresql-production",
        "file": "blog/03-postgresql-production.md",
        "date": "2026-03",
        "title": "PostgreSQL и продакшен — Nika CRM",
        "description": "Только PostgreSQL: миграции, bootstrap-дамп, бэкапы и Docker.",
        "heading": "PostgreSQL и продакшен",
        "teaser": "Рабочая БД — Postgres; SQLite не для новых установок.",
    },
    {
        "slug": "rbac-reports-salary",
        "file": "blog/02-rbac-reports-salary.md",
        "date": "2026-01",
        "title": "Права, отчёты и зарплата — Nika CRM",
        "description": "RBAC, отчёты руководителя и начисление зарплаты по заявкам.",
        "heading": "Права, отчёты, зарплата",
        "teaser": "Роли, сводные отчёты и ЗП после полной оплаты.",
    },
    {
        "slug": "core-orders-warehouse-cash",
        "file": "blog/01-core-orders-warehouse-cash.md",
        "date": "2026-01",
        "title": "Заявки, склад и касса — старт Nika CRM",
        "description": "Базовые модули: заявки на ремонт, клиенты, склад и касса.",
        "heading": "Заявки, склад и касса",
        "teaser": "Ядро сервисного центра: приём, запчасти, оплаты.",
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
