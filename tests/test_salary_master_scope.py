"""Мастер с salary.view не получает общеорганизационные итоги зарплаты."""
from app import create_app
from app.config import Config
from app.middleware.auth import User


class _CsrfOffConfig(Config):
    TESTING = True
    TRUSTED_HOSTS = ["localhost", "127.0.0.1"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


ORG_SENTINEL = {"total_revenue_cents": 999999, "orders_count": 42}


def _login(client, monkeypatch, *, user_id=7, role="master"):
    user_dict = {
        "id": user_id,
        "username": f"user-{role}",
        "role": role,
        "is_active": 1,
    }

    monkeypatch.setattr(
        "app.middleware.auth.UserService.get_user_by_id",
        lambda uid: user_dict if int(uid) == int(user_id) else None,
    )
    monkeypatch.setattr(
        "app.routes.salary_dashboard.UserService.check_permission",
        lambda uid, perm: perm == "salary.view",
    )
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
    return User(user_dict)


def _patch_salary_service(monkeypatch):
    calls = {"period": 0, "cash": 0, "profit": 0, "not_in": 0, "employees": 0}
    svc = "app.routes.salary_dashboard.SalaryDashboardService"

    def employees(**_kwargs):
        calls["employees"] += 1
        return [{"id": 7, "name": "Мастер", "role": "master"}]

    def period(**_kwargs):
        calls["period"] += 1
        return dict(ORG_SENTINEL)

    def cash(**_kwargs):
        calls["cash"] += 1
        return {"cash_income_total": 100.0, "salary_revenue_total": 90.0, "diff": 10.0}

    def profit(**_kwargs):
        calls["profit"] += 1
        return [{"order_id": 1, "profit_cents": 500}]

    def not_in(**_kwargs):
        calls["not_in"] += 1
        return [{"kind": "payment", "id": 1}]

    monkeypatch.setattr(f"{svc}.get_employees_with_stats", employees)
    monkeypatch.setattr(f"{svc}.get_salary_period_totals", period)
    monkeypatch.setattr(f"{svc}.get_cash_reconciliation", cash)
    monkeypatch.setattr(f"{svc}.get_profit_details_by_orders", profit)
    monkeypatch.setattr(f"{svc}.get_not_in_salary_items", not_in)
    return calls


def _assert_org_hidden(payload, calls):
    assert payload["period_totals"] is None
    assert payload["cash_reconciliation"] is None
    assert payload["profit_details"] == []
    assert payload["not_in_salary"] == []
    assert calls["period"] == 0
    assert calls["cash"] == 0
    assert calls["profit"] == 0
    assert calls["not_in"] == 0


def test_master_employees_api_hides_org_totals(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, role="master")
    calls = _patch_salary_service(monkeypatch)

    resp = client.get("/api/salary/employees")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    assert payload["employees"]
    _assert_org_hidden(payload, calls)
    assert calls["employees"] == 1


def test_master_custom_role_and_light_also_hide_org_totals(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, role="master_custom")
    calls = _patch_salary_service(monkeypatch)

    resp = client.get("/api/salary/employees?light=1")
    assert resp.status_code == 200
    _assert_org_hidden(resp.get_json(), calls)


def test_master_extras_api_hides_org_totals(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, role="master")
    calls = _patch_salary_service(monkeypatch)

    resp = client.get("/api/salary/extras")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    _assert_org_hidden(payload, calls)


def test_admin_still_gets_org_totals(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=1, role="admin")
    calls = _patch_salary_service(monkeypatch)

    resp = client.get("/api/salary/employees")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["period_totals"] == ORG_SENTINEL
    assert payload["cash_reconciliation"]["diff"] == 10.0
    assert payload["profit_details"]
    assert payload["not_in_salary"]
    assert calls["period"] == 1
    assert calls["cash"] == 1
    assert calls["profit"] == 1
    assert calls["not_in"] == 1


def test_manager_still_gets_org_totals(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=2, role="manager")
    calls = _patch_salary_service(monkeypatch)

    resp = client.get("/api/salary/extras")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["period_totals"] == ORG_SENTINEL
    assert calls["period"] == 1
    assert calls["cash"] == 1
