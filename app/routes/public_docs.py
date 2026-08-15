"""Публичные страницы документации на SEO-лендинге (без логина)."""
from __future__ import annotations

import logging
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    g,
    render_template,
    send_from_directory,
    url_for,
)

from app.routes.main import _landing_canonical_url, _public_landing_enabled, _windows_setup_info
from app.utils.public_markdown import docs_root, render_docs_markdown

bp = Blueprint("public_docs", __name__)
logger = logging.getLogger(__name__)

_PAGES = {
    "hub": {
        "title": "Документация бесплатной Nika CRM — руководства без GitHub",
        "description": (
            "Документация бесплатной open-source Nika CRM на демо-сайте: сценарий "
            "рабочего дня со скриншотами, полное руководство и установка."
        ),
        "keywords": (
            "документация Nika CRM, бесплатная CRM, руководство сервисный центр, "
            "сценарий рабочего дня, установка CRM, open source"
        ),
        "heading": "Как работать в Nika CRM",
        "nav": "hub",
        "path": "/docs",
    },
    "about": {
        "file": "ABOUT.md",
        "title": "О проекте и установка бесплатной Nika CRM — Windows, Docker, демо",
        "description": (
            "Что умеет бесплатная open-source CRM для сервисных центров: Windows SETUP, "
            "Docker, быстрый старт и контакты поддержки."
        ),
        "keywords": (
            "бесплатная CRM сервисный центр, open source CRM, Nika CRM установка, "
            "Windows SETUP, Docker CRM, о проекте Nika"
        ),
        "heading": "О проекте и установка",
        "nav": "about",
        "path": "/docs/about",
    },
    "guide": {
        "file": "USER_GUIDE.md",
        "title": "Руководство пользователя Nika CRM — заявки, диагностика, кабинет",
        "description": (
            "Руководство Nika Service CRM 3.4: диагностика заявки, личный кабинет "
            "с фото и чеком, устройства, платежи, чат и заявки, склад, касса."
        ),
        "keywords": (
            "руководство Nika CRM, диагностика заявки, личный кабинет клиента, "
            "печать чека, мои устройства, заявки ремонт, бесплатная CRM"
        ),
        "heading": "Руководство пользователя",
        "nav": "guide",
        "path": "/docs/guide",
    },
    "walkthrough": {
        "file": "USER_WALKTHROUGH.md",
        "title": "Сценарий рабочего дня в Nika CRM — от заявки до кассы",
        "description": (
            "Пошаговый сценарий бесплатной CRM: вход, создание заявки, услуги и товары, "
            "оплата, закрытие, зарплата и сведение кассы — со скриншотами."
        ),
        "keywords": (
            "сценарий рабочего дня CRM, заявка на ремонт, касса сервисный центр, "
            "скриншоты Nika CRM, walkthrough"
        ),
        "heading": "Пошаговый сценарий рабочего дня",
        "nav": "walkthrough",
        "path": "/docs/walkthrough",
    },
}


def _require_public_landing():
    if not _public_landing_enabled():
        abort(404)


def _common_ctx(slug: str, content_html: str | None = None) -> dict:
    meta = _PAGES[slug]
    canonical = _landing_canonical_url()
    path = meta["path"]
    page_url = f"{canonical}{path}"
    crumbs = [
        {"name": "Главная", "item": f"{canonical}/"},
        {"name": "Документация", "item": f"{canonical}/docs"},
    ]
    if slug != "hub":
        crumbs.append({"name": meta["heading"], "item": page_url})
    return {
        "canonical_url": canonical,
        "page_url": page_url,
        "page_path": path,
        "page_title": meta["title"],
        "page_description": meta["description"],
        "page_keywords": meta["keywords"],
        "page_heading": meta["heading"],
        "active_docs_nav": meta["nav"],
        "content_html": content_html,
        "github_url": "https://github.com/nika-sc/Nika-Service-CRM",
        "windows_setup": _windows_setup_info(),
        "og_image_url": f"{canonical}{url_for('static', filename='marketing/og-landing.jpg')}",
        "breadcrumb_items": crumbs,
        "schema_type": "WebPage" if slug == "hub" else "TechArticle",
    }


def _page_ctx(slug: str) -> dict:
    meta = _PAGES[slug]
    try:
        html = render_docs_markdown(meta["file"])
    except FileNotFoundError:
        logger.exception("Public docs file missing: %s", meta["file"])
        abort(404)
    return _common_ctx(slug, html)


@bp.before_request
def _mark_indexable():
    if _public_landing_enabled():
        g.allow_search_indexing = True


@bp.route("/docs")
def docs_hub():
    _require_public_landing()
    return render_template("marketing/docs_hub.html", **_common_ctx("hub"))


@bp.route("/docs/about")
def docs_about():
    _require_public_landing()
    return render_template("marketing/docs_page.html", **_page_ctx("about"))


@bp.route("/docs/guide")
def docs_guide():
    _require_public_landing()
    return render_template("marketing/docs_page.html", **_page_ctx("guide"))


@bp.route("/docs/walkthrough")
def docs_walkthrough():
    _require_public_landing()
    return render_template("marketing/docs_page.html", **_page_ctx("walkthrough"))


@bp.route("/docs/assets/walkthrough/<path:filename>")
def docs_walkthrough_asset(filename: str):
    _require_public_landing()
    if "/" in filename or "\\" in filename or ".." in filename:
        abort(404)
    safe = Path(filename).name
    folder = docs_root() / "assets" / "walkthrough"
    target = (folder / safe).resolve()
    try:
        target.relative_to(folder.resolve())
    except ValueError:
        abort(404)
    if not target.is_file():
        abort(404)
    return send_from_directory(folder, safe)
