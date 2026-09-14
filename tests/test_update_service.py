"""Windows SETUP update check: version compare, cache, opt-out, soft network errors."""
import json
from pathlib import Path

import pytest

from app.services import update_service as us


def test_version_compare_numeric_not_lexicographic():
    assert us.is_newer("1.0.10", "1.0.7")
    assert us.is_newer("1.0.9", "1.0.8")
    assert us.is_newer("1.0.8", "1.0.7")
    assert not us.is_newer("1.0.7", "1.0.7")
    assert not us.is_newer("1.0.6", "1.0.7")
    assert us.parse_version("1.0.9") == (1, 0, 9)


def test_status_disabled_makes_no_network(monkeypatch, tmp_path):
    monkeypatch.setenv("NIKACRM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "0")

    def boom(*_a, **_k):
        raise AssertionError("network must not be used when disabled")

    monkeypatch.setattr(us, "_fetch_manifest", boom)
    result = us.status(force=True)
    assert result["enabled"] is False
    assert result["update_available"] is False
    assert result["ok"] is True


def test_status_caches_and_respects_ttl(monkeypatch, tmp_path):
    monkeypatch.setenv("NIKACRM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "1")
    monkeypatch.setenv("UPDATE_CHECK_TTL_HOURS", "24")
    calls = {"n": 0}

    def fake_fetch(_url):
        calls["n"] += 1
        return {
            "version": "9.9.9",
            "sha256": "abc",
            "github_download_url": "https://example.invalid/setup.exe",
            "blog_url": "https://example.invalid/blog",
        }

    monkeypatch.setattr(us, "_fetch_manifest", fake_fetch)
    first = us.status(force=False)
    second = us.status(force=False)
    assert calls["n"] == 1
    assert first["update_available"] is True
    assert second["from_cache"] is True
    assert (tmp_path / "installer" / "update-check.json").is_file()


def test_status_network_error_is_soft(monkeypatch, tmp_path):
    monkeypatch.setenv("NIKACRM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("UPDATE_CHECK_ENABLED", "1")

    def fail(_url):
        raise us.urllib.error.URLError("offline")

    monkeypatch.setattr(us, "_fetch_manifest", fail)
    result = us.status(force=True)
    assert result["ok"] is False
    assert result["update_available"] is False
    assert result["error"]
    cached = json.loads((tmp_path / "installer" / "update-check.json").read_text(encoding="utf-8"))
    assert cached["ok"] is False
