"""
Рендеринг HTML-шаблонов печати (Товарный чек, Квитанция, Акт).
Используется в заявках и в продажах магазина.
"""
import re
from typing import Dict, List


def render_print_template(
    template_html: str,
    values: Dict[str, str],
    print_items: List[Dict[str, str]],
) -> str:
    """
    Рендерит HTML-шаблон печати: подставляет values и разворачивает цикл ITEMS.

    - data-for="ITEMS" с var-inline и ##KEY## внутри строки
    - <var-inline data-var="VAR">...</var-inline> и ##VAR## заменяются на values[VAR]
    - Санитизация через bleach при наличии
    """
    if not template_html or not isinstance(template_html, str):
        return ""

    # Разворачиваем цикл data-for="ITEMS"
    data_for_items = re.search(
        r'<(\w+)[^>]*\s+data-for\s*=\s*["\']ITEMS["\'][^>]*>(.*?)</\1>',
        template_html,
        re.IGNORECASE | re.DOTALL,
    )
    if data_for_items:
        tag_name = data_for_items.group(1)
        row_html = data_for_items.group(2)
        rows = []
        for item_vals in print_items:
            line = row_html
            for key, val in item_vals.items():
                line = re.sub(
                    r'<var-inline[^>]*\s+data-var\s*=\s*["\']'
                    + re.escape(key)
                    + r'["\'][^>]*>.*?</var-inline>',
                    (lambda m, v=val: v),
                    line,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                line = line.replace(f"##{key}##", val)
            rows.append(f"<{tag_name}>{line}</{tag_name}>")
        replacement = "".join(rows)
        template_html = (
            template_html[: data_for_items.start()]
            + replacement
            + template_html[data_for_items.end() :]
        )

    # Рендерим <var-inline data-var="...">...</var-inline>
    def _replace_var_inline(m: re.Match) -> str:
        var_name = m.group(1)
        return values.get(var_name, "")

    rendered_html = template_html
    _var_inline_patterns = [
        r'<var-inline[^>]*\s+data-var\s*=\s*"([^"]+)"[^>]*>.*?</var-inline>',
        r"<var-inline[^>]*\s+data-var\s*=\s*'([^']+)'[^>]*>.*?</var-inline>",
    ]
    for _pattern in _var_inline_patterns:
        prev = None
        while prev != rendered_html:
            prev = rendered_html
            rendered_html = re.sub(
                _pattern,
                _replace_var_inline,
                rendered_html,
                flags=re.IGNORECASE | re.DOTALL,
            )

    # Заменяем ##TAG##
    def _replace_hash_tag(m: re.Match) -> str:
        var_name = m.group(1)
        return values.get(var_name, f"##{var_name}##")

    rendered_html = re.sub(
        r"##([A-Za-z_][A-Za-z0-9_.-]*)##",
        _replace_hash_tag,
        rendered_html,
    )

    uuid_tags_list = [
        "701809f9-23dc-4346-aff4-0aef32523aef",
        "b6a8f943-e1b0-46e8-a321-b25fcfaf6976",
        "c5286c7d-44aa-4579-8258-935b003998cf",
        "c76b5bc7-7a68-4672-9542-cabaf2962600",
        "bc1ae9b1-7b8b-4da6-add5-26982865629e",
        "f93f4677-15b5-4e57-97e7-a345cb5b0e21",
        "dfd7aa33-fd89-462a-bbbc-39c1550415da",
    ]
    for uuid_tag in uuid_tags_list:
        if uuid_tag in values:
            rendered_html = rendered_html.replace(f"##{uuid_tag}##", values[uuid_tag])
            rendered_html = rendered_html.replace(
                f"##{uuid_tag.upper()}##", values[uuid_tag]
            )

    # Fallback: ограничения логотипа из настроек
    logo_url_safe = values.get("COMPANY_LOGO_URL", "")
    logo_style_safe = values.get("COMPANY_LOGO_STYLE", "")
    if logo_url_safe and logo_style_safe:

        def _ensure_logo_style(match: re.Match) -> str:
            img_tag = match.group(0)
            if re.search(r"\sstyle\s*=", img_tag, flags=re.IGNORECASE):
                return img_tag
            return img_tag[:-1] + f' style="{logo_style_safe}">'

        rendered_html = re.sub(
            r"<img\b[^>]*\bsrc\s*=\s*[\"']"
            + re.escape(logo_url_safe)
            + r"[\"'][^>]*>",
            _ensure_logo_style,
            rendered_html,
            flags=re.IGNORECASE,
        )

    try:
        from bleach import clean

        rendered_html = clean(
            rendered_html,
            tags=[
                "p", "table", "tbody", "tr", "td", "th",
                "h1", "h2", "h3", "h4", "h5", "h6",
                "strong", "em", "u", "ol", "ul", "li", "br",
                "img", "span", "div", "var-inline",
            ],
            attributes={
                "*": [
                    "style", "class", "width", "height", "border",
                    "colspan", "rowspan", "data-var", "data-for", "src", "alt",
                ]
            },
            strip=False,
        )
    except ImportError:
        pass

    return rendered_html
