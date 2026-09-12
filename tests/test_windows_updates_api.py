"""Public Windows SETUP manifest and admin-only update API."""
from app import create_app
from app.config import Config
from app.version import APP_VERSION


class _CsrfOffConfig(Config):
    TESTING = True
    TRUSTED_HOSTS = ["localhost", "127.0.0.1"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    UPDATE_CHECK_ENABLED = False


def test_windows_setup_latest_is_public():
    app = create_app(_CsrfOffConfig)
    client = app.test_client()
    resp = client.get("/api/windows-setup/latest")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["version"] == APP_VERSION
    assert "sha256" in data
    assert data["filename"].endswith("-x64.exe")
    assert data["github_download_url"]
    assert data["demo_download_url"]
    assert data["blog_url"]
    assert "max-age=3600" in (resp.headers.get("Cache-Control") or "")


def test_updates_api_requires_admin(monkeypatch):
    app = create_app(_CsrfOffConfig)

    def fake_user(user_id):
        role = "admin" if int(user_id) == 1 else "manager"
        return {
            "id": int(user_id),
            "username": role,
            "role": role,
            "is_active": 1,
        }

    monkeypatch.setattr(
        "app.services.user_service.UserService.get_user_by_id",
        staticmethod(fake_user),
    )
    client = app.test_client()
    anon = client.get("/api/updates/status")
    assert anon.status_code == 401

    with client.session_transaction() as sess:
        sess["_user_id"] = "2"
        sess["_fresh"] = True
    manager = client.get("/api/updates/status")
    assert manager.status_code == 403

    with client.session_transaction() as sess:
        sess["_user_id"] = "1"
        sess["_fresh"] = True
    admin = client.get("/api/updates/status")
    assert admin.status_code == 200
    body = admin.get_json()
    assert body["success"] is True
    assert body["installed_version"] == APP_VERSION
    assert body["enabled"] is False
