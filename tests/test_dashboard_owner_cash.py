"""Owner cash picture on the company dashboard: pocket vs leftover."""
from app.services.dashboard_service import (
    _is_director_draw_category_name,
    _owner_cash_picture,
)


def test_director_draw_name_matches_vyemka():
    assert _is_director_draw_category_name("Выемка наличных директором")
    assert _is_director_draw_category_name("выемка")
    assert _is_director_draw_category_name("Изъятие прибыли")
    assert _is_director_draw_category_name("Дивиденды")
    assert not _is_director_draw_category_name("Уведомления директору")
    assert not _is_director_draw_category_name("Зарплата")
    assert not _is_director_draw_category_name("Обед")


def test_owner_cash_splits_draw_salary_and_other():
    picture = _owner_cash_picture(
        {
            "total_income": 100_000,
            "total_expense": 60_000,
            "balance": 45_000,
            "opening_balance": 5_000,
            "by_category": [
                {
                    "id": 334,
                    "name": "Выемка наличных директором",
                    "type": "expense",
                    "total": 30_000,
                    "count": 4,
                    "color": "#e83e8c",
                },
                {
                    "id": 322,
                    "name": "Выплата зарплаты",
                    "type": "expense",
                    "total": 20_000,
                    "count": 2,
                },
                {
                    "id": 338,
                    "name": "Обед",
                    "type": "expense",
                    "total": 10_000,
                    "count": 8,
                },
                {
                    "id": 336,
                    "name": "Внутренний перевод (списание)",
                    "type": "expense",
                    "total": 5_000,
                    "count": 1,
                },
            ],
        }
    )
    assert picture["director_draw"] == 30_000
    assert picture["director_draw_found"] is True
    assert picture["director_draw_category_id"] == 334
    assert picture["salary_cash"] == 20_000
    assert picture["other_expenses"] == 10_000
    assert picture["after_costs"] == 70_000
    assert picture["leftover_in_cash"] == 40_000
    assert picture["took_more_than_earned"] is False
    assert picture["other_expenses_top"][0]["name"] == "Обед"
    assert picture["closing_balance"] == 45_000


def test_owner_cash_flags_when_draw_exceeds_period_surplus():
    picture = _owner_cash_picture(
        {
            "total_income": 50_000,
            "total_expense": 70_000,
            "balance": 1_000,
            "opening_balance": 21_000,
            "by_category": [
                {
                    "id": 1,
                    "name": "Выемка наличных директором",
                    "type": "expense",
                    "total": 40_000,
                    "count": 1,
                },
                {
                    "id": 2,
                    "name": "Зарплата",
                    "type": "expense",
                    "total": 30_000,
                    "count": 1,
                },
            ],
        }
    )
    assert picture["after_costs"] == 20_000
    assert picture["director_draw"] == 40_000
    assert picture["leftover_in_cash"] == -20_000
    assert picture["took_more_than_earned"] is True


def test_owner_cash_empty_without_categories():
    picture = _owner_cash_picture({})
    assert picture["director_draw"] == 0
    assert picture["director_draw_found"] is False
    assert picture["after_costs"] == 0
