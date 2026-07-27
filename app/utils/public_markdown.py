"""Рендер публичных Markdown-страниц для SEO-лендинга (PUBLIC_LANDING)."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import bleach
import markdown as md_lib

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DOCS_ROOT = _PROJECT_ROOT / "docs"

_ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union(
    {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "br", "hr", "pre", "code", "blockquote",
        "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
        "img", "span", "div", "strong", "em", "a",
    }
)
_ALLOWED_ATTRS = {
    **bleach.sanitizer.ALLOWED_ATTRIBUTES,
    "img": ["src", "alt", "title", "loading", "decoding", "class"],
    "a": ["href", "title", "rel", "target", "class"],
    "code": ["class"],
    "th": ["align"],
    "td": ["align"],
    "div": ["class"],
    "span": ["class"],
    "table": ["class"],
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
        output_format="html5",
    )
    return bleach.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        protocols=["http", "https", "mailto"],
        strip=True,
    )


def render_docs_markdown(rel_path: str) -> str:
    """rel_path относительно docs/, например USER_GUIDE.md."""
    path = _DOCS_ROOT / rel_path
    if not path.is_file():
        raise FileNotFoundError(rel_path)
    return _render_cached(rel_path, path.stat().st_mtime_ns)
