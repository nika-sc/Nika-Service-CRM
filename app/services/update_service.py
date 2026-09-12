"""Check the public Windows SETUP manifest for a newer installer.

Outbound traffic is a single GET of a public JSON. No install identity,
version or statistics are sent. Disabled with UPDATE_CHECK_ENABLED=false.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_NAME = "update-check.json"
_REQUEST_TIMEOUT_SEC = 5


def installed_version() -> str:
    from app.version import APP_VERSION

    return APP_VERSION


def parse_version(value: str) -> tuple:
    parts = []
    for chunk in (value or "").strip().split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


def _data_dir() -> Path:
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            configured = (current_app.config.get("NIKACRM_DATA_DIR") or "").strip()
            if configured:
                return Path(configured)
    except Exception:
        pass
    env_dir = (os.environ.get("NIKACRM_DATA_DIR") or "").strip()
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parents[2] / "data"


def _cache_path() -> Path:
    return _data_dir() / "installer" / _CACHE_NAME


def _ttl_hours() -> int:
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            return int(current_app.config.get("UPDATE_CHECK_TTL_HOURS") or 24)
    except Exception:
        pass
    try:
        return int(os.environ.get("UPDATE_CHECK_TTL_HOURS", "24"))
    except ValueError:
        return 24


def _check_enabled() -> bool:
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            return bool(current_app.config.get("UPDATE_CHECK_ENABLED"))
    except Exception:
        pass
    return os.environ.get("UPDATE_CHECK_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _manifest_url() -> str:
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            url = (current_app.config.get("UPDATE_MANIFEST_URL") or "").strip()
            if url:
                return url
    except Exception:
        pass
    return (
        os.environ.get("UPDATE_MANIFEST_URL")
        or "https://service.nika-crm.ru/api/windows-setup/latest"
    ).strip()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _read_cache() -> Optional[dict]:
    path = _cache_path()
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _write_cache(payload: dict) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not write update-check cache: %s", exc)


def _cache_is_fresh(payload: dict) -> bool:
    checked = _parse_iso(str(payload.get("checked_at") or ""))
    if not checked:
        return False
    return _now() - checked < timedelta(hours=_ttl_hours())


def _base_status() -> dict:
    from app.version import APP_BUILD_DATE

    return {
        "enabled": _check_enabled(),
        "installed_version": installed_version(),
        "installed_build_date": APP_BUILD_DATE,
        "update_available": False,
        "latest": None,
        "error": None,
        "checked_at": None,
        "from_cache": False,
    }


def peek_cached_status() -> Optional[dict]:
    """Return a cached status without touching the network. None if no cache."""
    cached = _read_cache()
    if not cached:
        return None
    result = _base_status()
    result.update({
        "update_available": bool(cached.get("update_available")),
        "latest": cached.get("latest"),
        "error": cached.get("error"),
        "checked_at": cached.get("checked_at"),
        "from_cache": True,
        "ok": cached.get("ok", cached.get("error") is None),
    })
    return result


def _fetch_manifest(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NikaCRM-UpdateCheck",
            "Accept": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_SEC) as response:
        body = response.read(65536)
    data = json.loads(body.decode("utf-8"))
    if not isinstance(data, dict) or not str(data.get("version") or "").strip():
        raise ValueError("manifest is missing version")
    return data


def status(force: bool = False) -> dict:
    result = _base_status()
    if not result["enabled"]:
        result["ok"] = True
        return result

    cached = _read_cache()
    if cached and not force and _cache_is_fresh(cached):
        result.update({
            "update_available": bool(cached.get("update_available")),
            "latest": cached.get("latest"),
            "error": cached.get("error"),
            "checked_at": cached.get("checked_at"),
            "from_cache": True,
            "ok": cached.get("ok", cached.get("error") is None),
        })
        return result

    url = _manifest_url()
    try:
        manifest = _fetch_manifest(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
        logger.info("Update check failed: %s", exc)
        checked_at = _now().isoformat()
        payload = {
            "ok": False,
            "error": "не удалось проверить обновления",
            "checked_at": checked_at,
            "update_available": False,
            "latest": (cached or {}).get("latest") if cached else None,
        }
        _write_cache(payload)
        result.update(payload)
        result["from_cache"] = False
        return result

    latest_version = str(manifest.get("version") or "").strip()
    checked_at = _now().isoformat()
    payload = {
        "ok": True,
        "error": None,
        "checked_at": checked_at,
        "update_available": is_newer(latest_version, result["installed_version"]),
        "latest": {
            "version": latest_version,
            "build_date": manifest.get("build_date"),
            "sha256": manifest.get("sha256"),
            "filename": manifest.get("filename"),
            "github_download_url": manifest.get("github_download_url"),
            "demo_download_url": manifest.get("demo_download_url"),
            "github_release_url": manifest.get("github_release_url"),
            "blog_url": manifest.get("blog_url"),
        },
    }
    _write_cache(payload)
    result.update(payload)
    result["from_cache"] = False
    return result


class UpdateService:
    installed_version = staticmethod(installed_version)
    parse_version = staticmethod(parse_version)
    is_newer = staticmethod(is_newer)
    peek_cached_status = staticmethod(peek_cached_status)
    status = staticmethod(status)
