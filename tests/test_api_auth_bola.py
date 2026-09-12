"""Role BOLA: salary report/debts/details/recalculate and portal IDOR."""
from types import SimpleNamespace

from app import create_app
from app.config import Config
from app.middleware.auth import User


class _CsrfOffConfig(Config):
    TESTING = True
    TRUSTED_HOSTS = ["localhost", "127.0.0.1"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


MASTER_EMPLOYEE_ID = 7
FOREIGN_MASTER_ID = 99
OWN_ORDER_ID = 10
FOREIGN_ORDER_ID = 11


def _login(client, monkeypatch, *, user_id=7, role="master", perms=None):
    user_dict = {
        "id": user_id,
        "username": f"user-{role}",
        "role": role,
        "is_active": 1,
    }
    allowed = set(perms if perms is not None else ("salary.view",))

    monkeypatch.setattr(
        "app.middleware.auth.UserService.get_user_by_id",
        lambda uid: user_dict if int(uid) == int(user_id) else None,
    )
    monkeypatch.setattr(
        "app.services.user_service.UserService.check_permission",
        lambda uid, perm: perm in allowed,
    )
    monkeypatch.setattr(
        "app.routes.salary.UserService.check_permission",
        lambda uid, perm: perm in allowed,
    )
    monkeypatch.setattr(
        "app.routes.salary_dashboard.UserService.check_permission",
        lambda uid, perm: perm in allowed,
    )
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
    return User(user_dict)


def _patch_master_employee(monkeypatch, employee_id=MASTER_EMPLOYEE_ID):
    monkeypatch.setattr(
        "app.routes.salary.SalaryDashboardService.get_employee_id_by_user",
        lambda uid, role: (employee_id, "master"),
    )
    monkeypatch.setattr(
        "app.routes.salary_dashboard.SalaryDashboardService.get_employee_id_by_user",
        lambda uid, role: (employee_id, "master"),
    )


def _patch_manager_employee(monkeypatch, employee_id=3):
    monkeypatch.setattr(
        "app.routes.salary.SalaryDashboardService.get_employee_id_by_user",
        lambda uid, role: (employee_id, "manager"),
    )


def _report_calls(monkeypatch):
    calls = []

    def fake_report(**kwargs):
        calls.append(kwargs)
        return {"accruals": [{"id": 1}], "summary": {"total_accruals": 1}}

    monkeypatch.setattr("app.routes.salary.SalaryService.get_salary_report", fake_report)
    return calls


def test_master_salary_report_ignores_foreign_master_id(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, role="master")
    _patch_master_employee(monkeypatch)
    calls = _report_calls(monkeypatch)

    resp = client.get(f"/api/salary/report?master_id={FOREIGN_MASTER_ID}")
    assert resp.status_code == 200
    assert calls == [
        {
            "date_from": None,
            "date_to": None,
            "user_id": MASTER_EMPLOYEE_ID,
            "role": "master",
        }
    ]


def test_master_custom_salary_report_scoped_to_self(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, role="master_custom")
    _patch_master_employee(monkeypatch)
    calls = _report_calls(monkeypatch)

    resp = client.get(f"/api/salary/report?manager_id={FOREIGN_MASTER_ID}")
    assert resp.status_code == 200
    assert calls[0]["user_id"] == MASTER_EMPLOYEE_ID
    assert calls[0]["role"] == "master"


def test_manager_salary_report_can_view_master(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=2, role="manager")
    _patch_manager_employee(monkeypatch)
    calls = _report_calls(monkeypatch)

    resp = client.get(f"/api/salary/report?master_id={FOREIGN_MASTER_ID}")
    assert resp.status_code == 200
    assert calls[0]["user_id"] == FOREIGN_MASTER_ID
    assert calls[0]["role"] == "master"


def test_viewer_salary_report_forbidden(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=5, role="viewer", perms=())
    calls = _report_calls(monkeypatch)

    resp = client.get("/api/salary/report")
    assert resp.status_code == 403
    assert calls == []


def test_master_debts_skips_org_query(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, role="master")
    calls = {"n": 0}

    def boom(**_kwargs):
        calls["n"] += 1
        return {"items": [{"employee_id": 1}], "totals": {"total_to_pay_cents": 9}}

    monkeypatch.setattr(
        "app.routes.salary_dashboard.SalaryDashboardService.get_salary_debts",
        boom,
    )

    resp = client.get("/api/salary/debts")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["success"] is True
    assert payload["data"]["items"] == []
    assert payload["data"]["totals"]["total_to_pay_cents"] == 0
    assert calls["n"] == 0


def test_admin_debts_still_loads_org_list(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=1, role="admin")
    monkeypatch.setattr(
        "app.routes.salary_dashboard.SalaryDashboardService.get_salary_debts",
        lambda **_k: {
            "items": [{"employee_id": 8, "owed_cents": 100}],
            "totals": {"total_to_pay_cents": 100, "total_debt_company_cents": 0},
        },
    )

    resp = client.get("/api/salary/debts")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["data"]["items"][0]["employee_id"] == 8


def test_master_recalculate_forbidden(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, role="master")
    calls = []

    def accrue(order_id, force_recalculate=False):
        calls.append((order_id, force_recalculate))
        return [1]

    monkeypatch.setattr("app.routes.salary.SalaryService.accrue_salary_for_order", accrue)

    resp = client.post("/api/salary/recalculate/10")
    assert resp.status_code == 403
    assert calls == []


def test_manager_recalculate_allowed(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=2, role="manager")
    calls = []

    def accrue(order_id, force_recalculate=False):
        calls.append((order_id, force_recalculate))
        return [3]

    monkeypatch.setattr("app.routes.salary.SalaryService.accrue_salary_for_order", accrue)

    resp = client.post("/api/salary/recalculate/10")
    assert resp.status_code == 200
    assert calls == [(10, True)]
    assert resp.get_json()["accrual_ids"] == [3]


def test_master_order_details_own_ok_foreign_forbidden(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, role="master")
    _patch_master_employee(monkeypatch)

    def fake_order(order_id):
        master_id = MASTER_EMPLOYEE_ID if int(order_id) == OWN_ORDER_ID else FOREIGN_MASTER_ID
        return SimpleNamespace(master_id=master_id)

    details_calls = []

    monkeypatch.setattr("app.routes.salary.OrderService.get_order", fake_order)
    monkeypatch.setattr(
        "app.routes.salary.SalaryService.get_order_accrual_details",
        lambda oid: details_calls.append(oid) or {"order_id": oid},
    )
    monkeypatch.setattr(
        "app.routes.salary.SalaryService.get_accruals_for_order",
        lambda oid: [{"order_id": oid}],
    )

    own = client.get(f"/api/salary/order/{OWN_ORDER_ID}/details")
    assert own.status_code == 200
    assert details_calls == [OWN_ORDER_ID]

    foreign = client.get(f"/api/salary/order/{FOREIGN_ORDER_ID}/details")
    assert foreign.status_code == 403

    foreign_list = client.get(f"/api/salary/order/{FOREIGN_ORDER_ID}")
    assert foreign_list.status_code == 403


def test_portal_customer_cannot_read_foreign_order(monkeypatch):
    app = create_app(_CsrfOffConfig)

    monkeypatch.setattr(
        "app.routes.customer_portal.OrderService.get_order_full_data",
        lambda order_id: {"order": {"id": order_id, "customer_id": 999}},
    )
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["portal_customer_id"] = 1
        sess["portal_customer_name"] = "Client"
    resp = client.get("/portal/api/order/5")
    assert resp.status_code == 403


def test_staff_cookie_does_not_open_portal_api(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=1, role="admin")
    resp = client.get("/portal/api/order/5")
    assert resp.status_code == 401


def test_viewer_cannot_use_search_api(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=5, role="viewer", perms=())
    calls = []

    monkeypatch.setattr(
        "app.routes.search.SearchService.global_search",
        lambda **_k: calls.append("search") or {},
    )
    monkeypatch.setattr(
        "app.routes.search.SearchService.autocomplete",
        lambda *_a, **_k: calls.append("ac") or [],
    )

    api = client.get("/search/api?q=ivan")
    auto = client.get("/search/api/autocomplete?q=iv")
    assert api.status_code == 403
    assert auto.status_code == 403
    assert calls == []


def test_staff_with_view_orders_can_search(monkeypatch):
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    _login(client, monkeypatch, user_id=3, role="manager", perms=("view_orders",))
    monkeypatch.setattr(
        "app.routes.search.SearchService.global_search",
        lambda **_k: {"orders": []},
    )

    resp = client.get("/search/api?q=ivan")
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
