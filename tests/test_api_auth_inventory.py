"""Defensive API auth: url_map inventory and unauthenticated 401 JSON."""
from app import create_app
from app.utils.json_api import PUBLIC_API_EXACT

from tests.api_auth_inventory import (
    ApiAuthTestConfig,
    is_public_api_path,
    iter_api_rules,
)


def test_public_api_allowlist_routes_exist():
    app = create_app(ApiAuthTestConfig)
    mapped = {rule.rule for rule in app.url_map.iter_rules()}
    missing = [path for path in sorted(PUBLIC_API_EXACT) if path not in mapped]
    assert missing == [], f"public allowlist path missing from url_map: {missing}"


def test_unauthenticated_api_returns_401_json_not_login_redirect():
    app = create_app(ApiAuthTestConfig)
    client = app.test_client()
    failures = []
    seen = set()
    public_hits = []

    for _rule, path, method in iter_api_rules(app):
        key = (method, path)
        if key in seen:
            continue
        seen.add(key)

        resp = client.open(path, method=method, base_url="http://127.0.0.1")
        location = resp.headers.get("Location") or ""
        ctype = (resp.headers.get("Content-Type") or "").lower()

        if is_public_api_path(path):
            if resp.status_code not in (200, 404):
                public_hits.append(
                    f"{method} {path} expected 200/404 for public API, got {resp.status_code}"
                )
            if "/login" in location:
                public_hits.append(f"{method} {path} public API redirected to login")
            continue

        if resp.status_code != 401:
            failures.append(f"{method} {path} -> {resp.status_code} (want 401)")
            continue
        if "/login" in location:
            failures.append(f"{method} {path} 401 but Location={location}")
            continue
        if "json" not in ctype:
            body = (resp.get_data(as_text=True) or "")[:120]
            failures.append(
                f"{method} {path} 401 without JSON Content-Type ({ctype!r}) body={body!r}"
            )

    assert not public_hits, "\n".join(public_hits)
    assert not failures, "Unauthenticated API must be 401 JSON, not login redirect:\n" + "\n".join(
        failures
    )
    assert len(seen) >= 40, f"too few API rules discovered: {len(seen)}"
