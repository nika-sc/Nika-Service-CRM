"""LAN Host allowlist: @private must not be blocked by Flask/Werkzeug."""
from app import (
    create_app,
    _hostname_from_host_header,
    _socketio_origin_allowed,
)
from app.config import Config
from app.utils.validators import parse_non_negative_money, money_values_equal
from app.utils.exceptions import ValidationError
import pytest


class _LanConfig(Config):
    TESTING = True
    TRUSTED_HOSTS = ['localhost', '127.0.0.1', '@private']
    SOCKETIO_CORS_ALLOWED_ORIGINS = 'http://localhost:5000,http://127.0.0.1:5000,@private'


def test_private_lan_ip_host_allowed():
    app = create_app(_LanConfig)
    assert app.config.get('TRUSTED_HOSTS') is None
    assert '@private' in (app.config.get('HOST_ALLOWLIST') or [])
    client = app.test_client()
    # Hyper-V / Windows Sandbox style address
    resp = client.get('/login', headers={'Host': '172.21.172.216:5000'})
    assert resp.status_code == 200
    assert b'is not trusted' not in resp.data


def test_ipv6_link_local_host_allowed():
    app = create_app(_LanConfig)
    client = app.test_client()
    resp = client.get('/login', headers={'Host': '[fe80::1]:5000'})
    assert resp.status_code == 200
    assert b'is not trusted' not in resp.data


def test_unknown_public_host_rejected():
    app = create_app(_LanConfig)
    client = app.test_client()
    resp = client.get('/login', headers={'Host': 'evil.example:5000'})
    assert resp.status_code == 400


def test_hostname_from_host_header_ipv4_and_ipv6():
    assert _hostname_from_host_header('172.21.172.216:5000') == '172.21.172.216'
    assert _hostname_from_host_header('[fe80::1]:5000') == 'fe80::1'
    assert _hostname_from_host_header('[::1]') == '::1'
    assert _hostname_from_host_header('localhost:5000') == 'localhost'


def test_socketio_origin_allows_any_private_ip_with_app_port():
    assert _socketio_origin_allowed(
        'http://172.21.172.216:5000',
        static_origins=set(),
        app_port=5000,
        allow_private=True,
    )
    assert not _socketio_origin_allowed(
        'http://172.21.172.216:5001',
        static_origins=set(),
        app_port=5000,
        allow_private=True,
    )
    assert not _socketio_origin_allowed(
        'http://8.8.8.8:5000',
        static_origins=set(),
        app_port=5000,
        allow_private=True,
    )


def test_parse_non_negative_money_accepts_comma_and_rejects_negative():
    assert parse_non_negative_money('1,5', 'Сумма') == 1.5
    assert parse_non_negative_money('', 'Сумма') == 0.0
    with pytest.raises(ValidationError):
        parse_non_negative_money('-1', 'Сумма')
    with pytest.raises(ValidationError):
        parse_non_negative_money('abc', 'Сумма')


def test_money_values_equal_normalizes_string_forms():
    assert money_values_equal('100', '100.0')
    assert money_values_equal(0, '0')
    assert not money_values_equal('10', '10.01')
