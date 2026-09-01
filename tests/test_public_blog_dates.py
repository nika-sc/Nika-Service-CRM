"""Blog date display: time first, then DD.MM.YYYY."""
from app.routes.public_blog import format_blog_date_ru, _post_view


def test_format_blog_date_ru_time_then_day_month_year():
    assert format_blog_date_ru("2026-08-22 11:30") == "11:30 22.08.2026"
    assert format_blog_date_ru("2026-08-09 17:45") == "17:45 09.08.2026"
    assert format_blog_date_ru("2026-01-10 12:00") == "12:00 10.01.2026"
    assert format_blog_date_ru("2026-08-22") == "22.08.2026"
    assert format_blog_date_ru("") == ""


def test_latest_blog_post_is_dashboard_owner_cash():
    from app.routes.public_blog import _POSTS

    assert _POSTS[0]["slug"] == "dashboard-owner-cash"
    assert _POSTS[0]["file"] == "blog/40-dashboard-owner-cash.md"


def test_post_view_keeps_iso_and_adds_display():
    view = _post_view({"slug": "x", "date": "2026-08-22 11:30"})
    assert view["date"] == "2026-08-22 11:30"
    assert view["date_iso"] == "2026-08-22T11:30"
    assert view["date_display"] == "11:30 22.08.2026"
