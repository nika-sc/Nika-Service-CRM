"""Client IP after ProxyFix. Do not read X-Forwarded-For here — the client can set it."""
from flask import has_request_context, request


def client_ip() -> str:
    """IP for lockout and rate keys: request.remote_addr only (ProxyFix already applied)."""
    if not has_request_context():
        return "unknown"
    return (request.remote_addr or "unknown").strip() or "unknown"
