"""JSON API path helpers (401 JSON vs HTML login redirect)."""

# Prefixes that must answer unauthenticated callers with JSON 401,
# not a redirect to /login.
JSON_API_PREFIXES = (
    "/api/",
    "/portal/api/",
    "/finance/api/",
    "/warehouse/api/",
    "/reports/api/",
    "/shop/api/",
    "/search/api",
)

# Intentionally public JSON. No staff/portal session, no PII.
PUBLIC_API_EXACT = frozenset(
    {
        "/api/windows-setup/latest",
        "/api/demo/online-count",
    }
)


def is_json_api_path(path: str) -> bool:
    p = path or ""
    return any(p.startswith(prefix) for prefix in JSON_API_PREFIXES)
