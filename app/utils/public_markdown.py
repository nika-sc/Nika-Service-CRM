"""Рендер публичных Markdown-страниц для SEO-лендинга (PUBLIC_LANDING)."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import bleach
import markdown as md_lib
from markdown.extensions.toc import slugify_unicode

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DOCS_ROOT = _PROJECT_ROOT / "docs"

_ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union(
    {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "br", "hr", "pre", "code", "blockquote",
        "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
        "img", "span", "div", "strong", "em", "a",
        "figure", "figcaption",
    }
)
_ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "img": ["src", "alt", "title", "loading", "decoding", "class"],
    "a": ["href", "title", "rel", "target", "class", "id"],
    "code": ["class"],
    "th": ["align"],
    "td": ["align"],
    "div": ["class", "id"],
    "span": ["class", "id"],
    "table": ["class"],
    "figure": ["class"],
    "figcaption": ["class"],
    # Якоря оглавления (#18-мобильный-доступ-и-pwa и т.п.) — id должен переживать bleach
    "h1": ["id"],
    "h2": ["id"],
    "h3": ["id"],
    "h4": ["id"],
    "h5": ["id"],
    "h6": ["id"],
}

_MD_LINK_MAP = {
    "USER_GUIDE.md": "/docs/guide",
    "USER_WALKTHROUGH.md": "/docs/walkthrough",
    "ABOUT.md": "/docs/about",
    "README.md": "/docs",
    "API.md": "https://github.com/nika-sc/Nika-Service-CRM/blob/main/docs/API.md",
}


def docs_root() -> Path:
    return _DOCS_ROOT


def _rewrite_markdown_links(text: str) -> str:
    def repl(match: re.Match) -> str:
        label, url = match.group(1), match.group(2)
        bare = url.split("#", 1)[0].strip()
        frag = ""
        if "#" in url:
            frag = "#" + url.split("#", 1)[1]
        name = Path(bare).name
        if name in _MD_LINK_MAP:
            return f"[{label}]({_MD_LINK_MAP[name]}{frag})"
        if bare.startswith("assets/walkthrough/"):
            return f"[{label}](/docs/{bare})"
        if bare.startswith("../"):
            return match.group(0)
        return match.group(0)

    text = re.sub(r"!\[([^\]]*)\]\((assets/walkthrough/[^)]+)\)", r"![\1](/docs/\2)", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, text)
    return text


@lru_cache(maxsize=32)
def _render_cached(rel_path: str, mtime_ns: int) -> str:
    path = _DOCS_ROOT / rel_path
    raw = path.read_text(encoding="utf-8")
    raw = _rewrite_markdown_links(raw)
    html = md_lib.markdown(
        raw,
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={
            # Кириллица в id, как в ручных ссылках оглавления (#9-касса-движение-денег)
            "toc": {"slugify": slugify_unicode},
        },
        output_format="html5",
    )
    # Один H1 на странице — заголовок уже в шаблоне
    html = re.sub(r"<h1\b[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.IGNORECASE | re.DOTALL)
    cleaned = bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return _enhance_html_a11y(cleaned)


def _enhance_html_a11y(html: str) -> str:
    """Добавляет lazy-loading, подписи к скриншотам; помечает внешние ссылки."""

    def img_repl(match: re.Match) -> str:
        tag = match.group(0)
        if "loading=" not in tag:
            tag = tag[:-1] + ' loading="lazy"' + tag[-1]
        if "decoding=" not in tag:
            tag = tag[:-1] + ' decoding="async"' + tag[-1]
        alt_m = re.search(r'\balt="([^"]*)"', tag, flags=re.IGNORECASE)
        if not alt_m:
            src_m = re.search(r'\bsrc="([^"]+)"', tag)
            name = Path(src_m.group(1)).name if src_m else "Скриншот"
            tag = tag[:-1] + f' alt="{name}"' + tag[-1]
            alt_text = name
        else:
            alt_text = (alt_m.group(1) or "").strip()
            if not alt_text:
                src_m = re.search(r'\bsrc="([^"]+)"', tag)
                alt_text = Path(src_m.group(1)).stem.replace("-", " ") if src_m else "Скриншот"
                tag = re.sub(r'\balt=""', f'alt="{alt_text}"', tag, count=1)
        # Уже в figure — не оборачиваем повторно
        return tag

    # Сначала нормализуем img, затем оборачиваем одиночные <p><img…></p> в figure+figcaption
    html = re.sub(r"<img\b[^>]*>", img_repl, html, flags=re.IGNORECASE)

    def figure_wrap(match: re.Match) -> str:
        img_tag = match.group(1)
        alt_m = re.search(r'\balt="([^"]*)"', img_tag, flags=re.IGNORECASE)
        caption = (alt_m.group(1) if alt_m else "").strip() or "Скриншот"
        return (
            f'<figure class="ml-docs-figure">{img_tag}'
            f'<figcaption class="ml-docs-figcaption">{caption}</figcaption></figure>'
        )

    html = re.sub(
        r"<p>\s*(<img\b[^>]*>)\s*</p>",
        figure_wrap,
        html,
        flags=re.IGNORECASE,
    )

    def a_repl(match: re.Match) -> str:
        tag, inner = match.group(1), match.group(2)
        href_m = re.search(r'\bhref="([^"]+)"', tag)
        href = href_m.group(1) if href_m else ""
        if href.startswith("http") and "target=" not in tag:
            if "rel=" not in tag:
                tag = tag[:-1] + ' rel="noopener noreferrer"' + tag[-1]
            tag = tag[:-1] + ' target="_blank"' + tag[-1]
            if "visually-hidden" not in inner:
                inner += ' <span class="visually-hidden">(откроется в новой вкладке)</span>'
        return f"{tag}{inner}</a>"

    return re.sub(r"(<a\b[^>]*>)(.*?)</a>", a_repl, html, flags=re.IGNORECASE | re.DOTALL)


def render_docs_markdown(rel_path: str) -> str:
    """rel_path относительно docs/, например USER_GUIDE.md."""
    path = _DOCS_ROOT / rel_path
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    return _render_cached(rel_path, path.stat().st_mtime_ns)
