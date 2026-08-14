"""Auth: do not trust X-Forwarded-For or HTML password length."""
import pytest

from app import create_app
from app.config import Config
from app.utils.exceptions import ValidationError
from app.utils.validators import (
    PASSWORD_MAX_LEN,
    password_eligible_for_verify,
    password_meets_policy,
    validate_new_password,
)


class _CsrfOffConfig(Config):
    TESTING = True
    DEBUG = True
    TRUSTED_HOSTS = ["localhost", "127.0.0.1"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


def test_client_ip_ignores_spoofed_x_forwarded_for():
    from app.routes.main import _login_client_ip
    from app.utils.request_ip import client_ip

    app = create_app(_CsrfOffConfig)
    with app.test_request_context(
        "/",
        environ_base={"REMOTE_ADDR": "203.0.113.10"},
        headers={"X-Forwarded-For": "9.9.9.9, 10.0.0.1"},
    ):
        from flask import request

        assert client_ip() == request.remote_addr
        assert _login_client_ip() == request.remote_addr
        assert client_ip() != "9.9.9.9"


def test_validate_new_password_min_6_max_256():
    with pytest.raises(ValidationError):
        validate_new_password("12345")
    with pytest.raises(ValidationError):
        validate_new_password("a" * (PASSWORD_MAX_LEN + 1))
    assert validate_new_password("123456") == "123456"
    assert password_meets_policy("abcdef")
    assert not password_meets_policy("a" * 5)
    assert not password_meets_policy("a" * (PASSWORD_MAX_LEN + 1))
    assert password_eligible_for_verify("x")
    assert not password_eligible_for_verify("x" * (PASSWORD_MAX_LEN + 1))


def test_user_service_create_change_use_server_password_policy():
    import inspect
    from app.services import user_service as us

    create_src = inspect.getsource(us.UserService.create_user)
    change_src = inspect.getsource(us.UserService.change_password)
    assert "validate_new_password" in create_src
    assert "validate_new_password" in change_src
    assert "len(password) < 4" not in create_src
    assert "len(new_password) < 4" not in change_src


def test_staff_login_oversized_password_does_not_verify(monkeypatch):
    calls = []

    def boom(*_a, **_k):
        calls.append(1)
        raise AssertionError("verify_password must not run for oversized password")

    monkeypatch.setattr("app.services.user_service.UserService.verify_password", boom)
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    resp = client.post(
        "/login",
        data={"username": "anyone", "password": "x" * (PASSWORD_MAX_LEN + 1)},
        follow_redirects=True,
    )
    assert calls == []
    assert resp.status_code in (200, 302, 400)
