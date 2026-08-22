"""SSRF-safe HTTP GET: resolve once, connect to that public IP, no second DNS."""
from __future__ import annotations

import ipaddress
import socket
import ssl
from http.client import HTTPConnection, HTTPSConnection, HTTPException
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

_MAX_REDIRECTS = 3
_BLOCKED_HOSTNAMES = frozenset({"localhost", "metadata.google.internal"})


class _PinnedHTTPConnection(HTTPConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float):
        super().__init__(host, port=port, timeout=timeout)
        self._pin_ip = ip

    def connect(self):
        self.sock = socket.create_connection((self._pin_ip, self.port), self.timeout)


class _PinnedHTTPSConnection(HTTPSConnection):
    def __init__(self, host: str, port: int, ip: str, timeout: float, context: ssl.SSLContext):
        super().__init__(host, port=port, timeout=timeout, context=context)
        self._pin_ip = ip

    def connect(self):
        sock = socket.create_connection((self._pin_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _ip_is_blocked(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def resolve_public_http_target(raw_url: str) -> Optional[Tuple[str, str, int, str, str]]:
    """
    Parse URL and resolve DNS once.
    Returns (scheme, hostname, port, ip, request_path) or None if unsafe.
    """
    try:
        parsed = urlparse(raw_url)
        if parsed.scheme not in ("http", "https"):
            return None
        hostname = (parsed.hostname or "").strip().rstrip(".")
        if not hostname or hostname.lower() in _BLOCKED_HOSTNAMES:
            return None
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80
        if port <= 0 or port > 65535:
            return None
        infos = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
        public_ips = []
        for info in infos:
            ip = info[4][0]
            ip_obj = ipaddress.ip_address(ip)
            if _ip_is_blocked(ip_obj):
                return None
            public_ips.append(ip)
        if not public_ips:
            return None
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return parsed.scheme, hostname, int(port), public_ips[0], path
    except Exception:
        return None


def is_safe_public_http_url(raw_url: str) -> bool:
    return resolve_public_http_target(raw_url) is not None


def fetch_public_http(
    raw_url: str,
    *,
    timeout: float = 8,
    max_bytes: int = 2 * 1024 * 1024,
    user_agent: str = "NikaCRM-logo-proxy/1.0",
    _hops: int = 0,
) -> Optional[Tuple[bytes, str]]:
    """
    GET a public http(s) URL. Connects to the resolved IP (no DNS rebinding).
    Redirects are re-validated. Failure → None.
    """
    if _hops > _MAX_REDIRECTS:
        return None
    planned = resolve_public_http_target(raw_url)
    if not planned:
        return None
    scheme, hostname, port, ip, path = planned
    conn = None
    try:
        if scheme == "https":
            conn = _PinnedHTTPSConnection(
                hostname, port, ip, timeout, ssl.create_default_context()
            )
        else:
            conn = _PinnedHTTPConnection(hostname, port, ip, timeout)
        conn.request(
            "GET",
            path,
            headers={
                "Host": hostname,
                "User-Agent": user_agent,
                "Accept": "image/*,*/*;q=0.8",
                "Connection": "close",
            },
        )
        resp = conn.getresponse()
        if resp.status in (301, 302, 303, 307, 308):
            location = resp.getheader("Location") or ""
            resp.read()
            next_url = urljoin(raw_url, location)
            return fetch_public_http(
                next_url,
                timeout=timeout,
                max_bytes=max_bytes,
                user_agent=user_agent,
                _hops=_hops + 1,
            )
        if resp.status != 200:
            return None
        length = resp.getheader("Content-Length")
        if length:
            try:
                if int(length) > max_bytes:
                    return None
            except (TypeError, ValueError):
                pass
        chunks = []
        total = 0
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                return None
            chunks.append(chunk)
        content_type = resp.getheader("Content-Type") or "application/octet-stream"
        return b"".join(chunks), content_type.split(";", 1)[0].strip() or "application/octet-stream"
    except (OSError, HTTPException, TimeoutError, ValueError, ssl.SSLError):
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
