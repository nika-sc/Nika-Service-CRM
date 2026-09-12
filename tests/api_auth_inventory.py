"""Allowlist and helpers for Service CRM JSON API auth tests."""
from __future__ import annotations

import re

from app.config import Config
from app.utils.json_api import PUBLIC_API_EXACT, is_json_api_path


class ApiAuthTestConfig(Config):
    TESTING = True
    TRUSTED_HOSTS = ["localhost", "127.0.0.1"]
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


def is_public_api_path(path: str) -> bool:
    return path in PUBLIC_API_EXACT


def concrete_path(rule_template: str) -> str:
    """Fill Werkzeug converters with harmless dummy values (no payload)."""

    def _repl(match: re.Match) -> str:
        inner = match.group(1)
        if ":" in inner:
            conv, name = inner.split(":", 1)
        else:
            conv, name = "string", inner
        if name == "role":
            return "master"
        if conv == "int":
            return "1"
        if conv == "path":
            return "x"
        return "1"

    return re.sub(r"<([^>]+)>", _repl, rule_template)


def pick_method(rule) -> str:
    methods = {m for m in (rule.methods or set()) if m not in {"HEAD", "OPTIONS"}}
    for preferred in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        if preferred in methods:
            return preferred
    return "GET"


def iter_api_rules(app):
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        path = concrete_path(rule.rule)
        if not is_json_api_path(path) and path not in PUBLIC_API_EXACT:
            continue
        yield rule, path, pick_method(rule)
