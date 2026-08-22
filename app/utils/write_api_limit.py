"""Write-API throttle shared across gunicorn workers (Redis INCR / 60s TTL)."""
from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

_memory_lock = threading.Lock()
_memory_buckets: dict = defaultdict(deque)


def reset_memory_for_tests() -> None:
    with _memory_lock:
        _memory_buckets.clear()


def allow_write(ip: str, limit: int) -> bool:
    """
    Record one write and return True if still under limit.
    Redis: INCR + EXPIRE 60s. Without Redis: in-process sliding 60s window.
    """
    identity = (ip or "unknown").strip() or "unknown"
    cap = int(limit or 0)
    if cap <= 0:
        return True

    from app.utils import login_lockout

    client = login_lockout._redis_client()
    if client is not None:
        key = f"nikacrm:writeapi:{identity}"
        try:
            count = int(client.incr(key))
            if count == 1:
                client.expire(key, 60)
            return count <= cap
        except Exception as exc:
            logger.debug("write-api redis incr failed: %s", exc)

    now = time.time()
    window_start = now - 60.0
    with _memory_lock:
        bucket = _memory_buckets[identity]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= cap:
            return False
        bucket.append(now)
        return True
