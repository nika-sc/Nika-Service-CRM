"""
Санитизация HTML печатных и email-шаблонов.

bleach ≥ 6.1 при разрешённом атрибуте style без css_sanitizer вычищает
все CSS-свойства (в т.ч. font-size). Здесь передаём CSSSanitizer с
whitelist типографики и вёрстки.
"""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

PRINT_TEMPLATE_TAGS: List[str] = [
    "html",
    "head",
    "body",
    "meta",
    "title",
    "style",
    "p",
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "td",
    "th",
    "colgroup",
    "col",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "ol",
    "ul",
    "li",
    "br",
    "hr",
    "img",
    "span",
    "div",
    "a",
    "var-inline",
]

PRINT_TEMPLATE_ATTRIBUTES: Dict[str, List[str]] = {
    "*": [
        "style",
        "class",
        "width",
        "height",
        "border",
        "cellpadding",
        "cellspacing",
        "colspan",
        "rowspan",
        "valign",
        "align",
        "data-var",
        "data-for",
        "src",
        "alt",
        "data-file-id",
        "charset",
        "name",
        "content",
        "href",
        "target",
        "rel",
    ]
}

EMAIL_TEMPLATE_TAGS: List[str] = [
    "p",
    "table",
    "tbody",
    "tr",
    "td",
    "th",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "em",
    "u",
    "ol",
    "ul",
    "li",
    "br",
    "img",
    "span",
    "div",
    "a",
    "var-inline",
]

EMAIL_TEMPLATE_ATTRIBUTES: Dict[str, List[str]] = {
    "*": [
        "style",
        "class",
        "width",
        "height",
        "border",
        "colspan",
        "rowspan",
        "data-var",
        "src",
        "alt",
        "href",
        "target",
        "rel",
    ]
}

# Узкий whitelist для рендера на странице заявки (исторический набор).
ORDER_RENDER_TAGS: List[str] = [
    "p",
    "table",
    "tbody",
    "tr",
    "td",
    "th",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "strong",
    "em",
    "u",
    "ol",
    "ul",
    "li",
    "br",
    "img",
    "span",
    "div",
    "var-inline",
]

ORDER_RENDER_ATTRIBUTES: Dict[str, List[str]] = {
    "*": [
        "style",
        "class",
        "width",
        "height",
        "border",
        "colspan",
        "rowspan",
        "data-var",
        "data-for",
        "src",
        "alt",
    ]
}

ALLOWED_CSS_PROPERTIES: List[str] = [
    "font-size",
    "font-family",
    "font-weight",
    "font-style",
    "line-height",
    "letter-spacing",
    "color",
    "background-color",
    "margin",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "text-align",
    "vertical-align",
    "text-decoration",
    "border",
    "border-width",
    "border-style",
    "border-color",
    "border-collapse",
    "border-top",
    "border-right",
    "border-bottom",
    "border-left",
    "width",
    "height",
    "max-width",
    "max-height",
    "min-width",
    "min-height",
    "display",
    "opacity",
    "white-space",
    "box-sizing",
]


def _build_css_sanitizer():
    try:
        from bleach.css_sanitizer import CSSSanitizer

        return CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)
    except Exception as exc:  # ImportError или отсутствие tinycss2
        logger.warning(
            "CSSSanitizer unavailable (%s); inline CSS properties may be stripped",
            exc,
        )
        return None


_CSS_SANITIZER = _build_css_sanitizer()


def sanitize_template_html(
    html: str,
    *,
    tags: Optional[Iterable[str]] = None,
    attributes: Optional[Dict[str, List[str]]] = None,
    protocols: Optional[Iterable[str]] = None,
    strip_comments: bool = False,
) -> str:
    """Sanitize template HTML, preserving whitelisted inline CSS (font-size, …)."""
    if html is None:
        return ""
    try:
        from bleach import clean
    except ImportError:
        return html

    kwargs = {
        "tags": list(tags) if tags is not None else PRINT_TEMPLATE_TAGS,
        "attributes": attributes if attributes is not None else PRINT_TEMPLATE_ATTRIBUTES,
        "strip": False,
    }
    if protocols is not None:
        kwargs["protocols"] = list(protocols)
    if strip_comments:
        kwargs["strip_comments"] = True
    if _CSS_SANITIZER is not None:
        kwargs["css_sanitizer"] = _CSS_SANITIZER

    return clean(html, **kwargs)


def sanitize_print_template_html(html: str) -> str:
    return sanitize_template_html(
        html,
        tags=PRINT_TEMPLATE_TAGS,
        attributes=PRINT_TEMPLATE_ATTRIBUTES,
    )


def sanitize_email_template_html(html: str) -> str:
    return sanitize_template_html(
        html,
        tags=EMAIL_TEMPLATE_TAGS,
        attributes=EMAIL_TEMPLATE_ATTRIBUTES,
    )


def sanitize_order_print_html(html: str) -> str:
    return sanitize_template_html(
        html,
        tags=ORDER_RENDER_TAGS,
        attributes=ORDER_RENDER_ATTRIBUTES,
        protocols=["http", "https", "data"],
        strip_comments=True,
    )
