"""Публичные страницы документации на SEO-лендинге (без логина)."""
from __future__ import annotations

import logging
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
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
    "about": {
        "file": "ABOUT.md",
        "title": "О проекте и установка — Nika CRM",
        "nav": "about",
        "heading": "О проекте и установка",
    },
    "guide": {
        "file": "USER_GUIDE.md",
        "title": "Руководство пользователя — Nika CRM",
        "nav": "guide",
        "heading": "Руководство пользователя",
    },
    "walkthrough": {
        "file": "USER_WALKTHROUGH.md",
        "title": "Сценарий рабочего дня — Nika CRM",
        "nav": "walkthrough",
        "heading": "Пошаговый сценарий рабочего дня",
    },
}


def _require_public_landing():
    if not _public_landing_enabled():
        abort(404)


def _page_ctx(slug: str) -> dict:
    meta = _PAGES[slug]
    try:
        html = render_docs_markdown(meta["file"])
    except FileNotFoundError:
        logger.exception("Public docs file missing: %s", meta["file"])
        abort(404)
    canonical = _landing_canonical_url()
    return {
        "canonical_url": canonical,
        "page_title": meta["title"],
        "page_heading": meta["heading"],
        "active_docs_nav": meta["nav"],
        "content_html": html,
        "github_url": "https://github.com/nika-sc/Nika-Service-CRM",
        "windows_setup": _windows_setup_info(),
        "og_image_url": f"{canonical}{url_for('static', filename='marketing/og-landing.jpg')}",
    }


@bp.before_request
def _mark_indexable():
    if _public_landing_enabled():
        g.allow_search_indexing = True


@bp.route("/docs")
def docs_hub():
    _require_public_landing()
    canonical = _landing_canonical_url()
    return render_template(
        "marketing/docs_hub.html",
        canonical_url=canonical,
        page_title="Документация — Nika CRM",
        active_docs_nav="hub",
        github_url="https://github.com/nika-sc/Nika-Service-CRM",
        windows_setup=_windows_setup_info(),
        og_image_url=f"{canonical}{url_for('static', filename='marketing/og-landing.jpg')}",
    )


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
