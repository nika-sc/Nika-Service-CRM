"""
Общий lockout входа (staff / portal) для нескольких gunicorn-воркеров.

Redis (REDIS_URL), если доступен; иначе in-memory на процесс.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Optional

logger = logging.getLogger(__name__)

_memory_lock = threading.Lock()
_memory_failures: dict = defaultdict(deque)
_memory_lockouts: dict = {}
_redis_by_url: dict = {}


def reset_memory_for_tests() -> None:
    """Сбрасывает in-memory счётчики (только тесты)."""
    with _memory_lock:
        _memory_failures.clear()
        _memory_lockouts.clear()


def _redis_client():
    url = None
    try:
        from flask import has_app_context, current_app
        if has_app_context():
            url = (current_app.config.get("REDIS_URL") or "").strip() or None
    except Exception:
        url = None
    if url:
        cached = _redis_by_url.get(url)
        if cached is not None:
            return cached
        try:
            import redis
            client = redis.from_url(url, decode_responses=True, socket_connect_timeout=1, socket_timeout=1)
            client.ping()
            _redis_by_url[url] = client
            return client
        except Exception as exc:
            logger.debug("login lockout: Redis недоступен (%s), in-memory", exc)
            return None
    try:
        from app.utils import cache as cache_mod
        return getattr(cache_mod, "_redis_client", None)
    except Exception:
        return None


def _cfg(scope: str) -> tuple[int, int, int]:
    prefix = "LOGIN" if scope == "staff" else "PORTAL_LOGIN"
    defaults = (8, 600, 900) if scope == "staff" else (10, 600, 900)
    try:
        from flask import has_app_context, current_app
        if has_app_context():
            threshold = int(current_app.config.get(f"{prefix}_LOCKOUT_THRESHOLD", defaults[0]) or defaults[0])
            window = int(current_app.config.get(f"{prefix}_LOCKOUT_WINDOW_SEC", defaults[1]) or defaults[1])
            duration = int(current_app.config.get(f"{prefix}_LOCKOUT_DURATION_SEC", defaults[2]) or defaults[2])
            return threshold, window, duration
    except Exception:
        pass
    return defaults


def _fail_key(scope: str, identity_key: str) -> str:
    return f"nikacrm:lockout:{scope}:fail:{identity_key}"


def _block_key(scope: str, identity_key: str) -> str:
    return f"nikacrm:lockout:{scope}:block:{identity_key}"


def is_locked(scope: str, identity_key: str) -> bool:
    if not identity_key:
        return False
    client = _redis_client()
    if client is not None:
        try:
            return bool(client.get(_block_key(scope, identity_key)))
        except Exception as exc:
            logger.debug("login lockout redis get failed: %s", exc)
    now = time.time()
    with _memory_lock:
        locked_until = _memory_lockouts.get((scope, identity_key), 0)
        if locked_until <= now:
            _memory_lockouts.pop((scope, identity_key), None)
            return False
        return True


def register_failure(scope: str, identity_key: str) -> bool:
    """Учитывает неудачу. True, если только что включили lockout."""
    if not identity_key:
        return False
    threshold, window_sec, lockout_sec = _cfg(scope)
    client = _redis_client()
    if client is not None:
        try:
            fail_key = _fail_key(scope, identity_key)
            count = int(client.incr(fail_key) or 0)
            if count == 1:
                client.expire(fail_key, int(window_sec))
            if count >= threshold:
                client.set(_block_key(scope, identity_key), "1", ex=int(lockout_sec))
                client.delete(fail_key)
                logger.warning("%s login lockout activated for key=%s", scope, identity_key)
                return True
            return False
        except Exception as exc:
            logger.debug("login lockout redis incr failed: %s", exc)
    now = time.time()
    mem_key = (scope, identity_key)
    with _memory_lock:
        bucket = _memory_failures[mem_key]
        window_start = now - float(window_sec)
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        bucket.append(now)
        if len(bucket) >= threshold:
            _memory_lockouts[mem_key] = now + float(lockout_sec)
            bucket.clear()
            logger.warning("%s login lockout activated for key=%s", scope, identity_key)
            return True
        return False


def clear(scope: str, identity_key: str) -> None:
    if not identity_key:
        return
    client = _redis_client()
    if client is not None:
        try:
            client.delete(_fail_key(scope, identity_key), _block_key(scope, identity_key))
        except Exception as exc:
            logger.debug("login lockout redis delete failed: %s", exc)
    mem_key = (scope, identity_key)
    with _memory_lock:
        _memory_failures.pop(mem_key, None)
        _memory_lockouts.pop(mem_key, None)
