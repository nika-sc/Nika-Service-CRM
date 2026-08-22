"""Same-host redirect targets (login next=, error referrer)."""
from urllib.parse import urljoin, urlparse


def is_safe_redirect_target(target: str) -> bool:
    """True if target is http(s) on the current request host."""
    if not target:
        return False
    try:
        from flask import has_request_context, request

        if not has_request_context():
            return False
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc
    except Exception:
        return False
