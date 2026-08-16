"""Tests for print/email template HTML sanitizer (font-size preservation)."""

from app.utils.template_html_sanitizer import (
    sanitize_email_template_html,
    sanitize_order_print_html,
    sanitize_print_template_html,
)


def test_print_template_preserves_font_size():
    html = '<p><span style="font-size: 18px; color: red;">X</span></p>'
    out = sanitize_print_template_html(html)
    assert "font-size: 18px" in out
    assert "color: red" in out
    assert "X" in out


def test_email_template_preserves_font_size():
    html = '<p><span style="font-size: 14pt;">Hello</span></p>'
    out = sanitize_email_template_html(html)
    assert "font-size: 14pt" in out
    assert "Hello" in out


def test_order_render_preserves_font_size():
    html = '<table><tr><td style="font-size: 10px;">Row</td></tr></table>'
    out = sanitize_order_print_html(html)
    assert "font-size: 10px" in out


def test_strips_javascript_href():
    html = '<a href="javascript:alert(1)">click</a>'
    out = sanitize_print_template_html(html)
    assert "javascript:" not in out.lower()


def test_keeps_safe_styles_only_by_property_name():
    # CSSSanitizer whitelists property names; unknown props are dropped.
    html = '<div style="font-size: 12px; position: fixed; top: 0;">x</div>'
    out = sanitize_print_template_html(html)
    assert "font-size: 12px" in out
    assert "position" not in out.lower()


def test_empty_estimated_cost_hides_line_and_literal_newline():
    from app.utils.print_template_renderer import render_print_template

    html = (
        '<p><strong>Предварительная стоимость: ##ESTIMATED_COST## ##CURRENCY##</strong></p>\\n'
        '<p><strong>Предоплата: ##TOTAL_PAID##</strong></p>'
    )
    out = render_print_template(
        html,
        {"ESTIMATED_COST": "", "CURRENCY": "RUB", "TOTAL_PAID": "0.00"},
        [],
    )
    assert "\\n" not in out
    assert "Предварительная стоимость" not in out
    assert "Предоплата: 0.00" in out


def test_estimated_cost_shown_when_set():
    from app.utils.print_template_renderer import render_print_template

    html = (
        '<p><strong>Предварительная стоимость: ##ESTIMATED_COST## ##CURRENCY##</strong></p>\\n'
        '<p><strong>Предоплата: ##TOTAL_PAID##</strong></p>'
    )
    out = render_print_template(
        html,
        {"ESTIMATED_COST": "1500.00", "CURRENCY": "RUB", "TOTAL_PAID": "0.00"},
        [],
    )
    assert "\\n" not in out
    assert "1500.00" in out
    assert "Предварительная стоимость" in out
