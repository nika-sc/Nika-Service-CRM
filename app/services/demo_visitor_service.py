"""
Демо-статистика заходов и онлайн-присутствия (DEMO_VISITOR_STATS).

Онлайн считается по экземпляру браузера (client_instance_id), а не по user_id:
один demo_admin в Chrome + Firefox = 2 онлайн.
"""
from __future__ import annotations

import hashlib
import logging
import random
import re
from datetime import timedelta
from typing import Any, Dict, List, Optional

from flask import current_app, has_request_context, request

from app.database.connection import get_db_connection
from app.utils.datetime_utils import get_moscow_now, get_moscow_now_str

logger = logging.getLogger(__name__)

ONLINE_WINDOW_MINUTES = 5
RETENTION_DAYS = 30
HEARTBEAT_THROTTLE_SECONDS = 45

# Fallback-ключ = тот же алгоритм, что fingerprint_client_instance_id() в Python
# (fp_ + sha256(user_id|ip|ua[:120])[:32]). Postgres: encode(sha256(...),'hex').
_FP_BASIS_SQL = """(
    COALESCE(CAST(user_id AS TEXT), '0')
    || '|'
    || COALESCE(ip, '')
    || '|'
    || SUBSTR(COALESCE(user_agent, ''), 1, 120)
)"""
_FP_BASIS_SQL_E = """(
    COALESCE(CAST(e.user_id AS TEXT), '0')
    || '|'
    || COALESCE(e.ip, '')
    || '|'
    || SUBSTR(COALESCE(e.user_agent, ''), 1, 120)
)"""
_SESSION_KEY_SQL = f"""
COALESCE(
    NULLIF(TRIM(COALESCE(client_instance_id, '')), ''),
    'fp_' || SUBSTR(ENCODE(SHA256(CONVERT_TO({_FP_BASIS_SQL}, 'UTF8')), 'hex'), 1, 32)
)
"""
_SESSION_KEY_SQL_E = f"""
COALESCE(
    NULLIF(TRIM(COALESCE(e.client_instance_id, '')), ''),
    'fp_' || SUBSTR(ENCODE(SHA256(CONVERT_TO({_FP_BASIS_SQL_E}, 'UTF8')), 'hex'), 1, 32)
)
"""


class DemoVisitorService:
    """Сервис демо-аналитики посещений CRM."""

    @staticmethod
    def is_enabled() -> bool:
        try:
            return bool(current_app.config.get("DEMO_VISITOR_STATS"))
        except RuntimeError:
            return False

    @staticmethod
    def client_ip() -> str:
        from app.utils.request_ip import client_ip as _client_ip
        return _client_ip()

    @staticmethod
    def client_user_agent() -> str:
        if not has_request_context():
            return ""
        return (request.headers.get("User-Agent") or "")[:500]

    @staticmethod
    def normalize_client_instance_id(value: Optional[str]) -> Optional[str]:
        raw = (value or "").strip()
        if not raw:
            return None
        # uuid / hex / safe token
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", raw):
            return None
        return raw[:80]

    @staticmethod
    def fingerprint_client_instance_id(
        user_id: Optional[int],
        ip: str,
        user_agent: str,
    ) -> str:
        """Стабильный fallback-ключ, если браузер не прислал client_instance_id."""
        basis = f"{user_id or 0}|{ip or ''}|{(user_agent or '')[:120]}"
        return "fp_" + hashlib.sha256(basis.encode("utf-8", errors="ignore")).hexdigest()[:32]

    @staticmethod
    def record_event(
        event_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        path: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        client_instance_id: Optional[str] = None,
    ) -> None:
        if not DemoVisitorService.is_enabled():
            return
        event_type = (event_type or "").strip().lower()
        if event_type not in ("login", "heartbeat", "logout"):
            return

        ip = (ip or DemoVisitorService.client_ip())[:64]
        user_agent = (user_agent or DemoVisitorService.client_user_agent())[:500]
        path = (path or "")[:500] or None
        username = (username or "")[:120] or None
        client_instance_id = DemoVisitorService.normalize_client_instance_id(client_instance_id)
        if not client_instance_id:
            client_instance_id = DemoVisitorService.fingerprint_client_instance_id(
                user_id, ip, user_agent
            )
        now_str = get_moscow_now_str()

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                if event_type == "heartbeat":
                    throttle_from = (
                        get_moscow_now() - timedelta(seconds=HEARTBEAT_THROTTLE_SECONDS)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    cur.execute(
                        """
                        SELECT 1 FROM demo_visitor_events
                        WHERE client_instance_id = ?
                          AND event_type = 'heartbeat'
                          AND created_at >= ?
                        LIMIT 1
                        """,
                        (client_instance_id, throttle_from),
                    )
                    if cur.fetchone():
                        return

                cur.execute(
                    """
                    INSERT INTO demo_visitor_events
                        (user_id, username, ip, user_agent, path, event_type, created_at, client_instance_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        ip,
                        user_agent,
                        path,
                        event_type,
                        now_str,
                        client_instance_id,
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.debug("demo_visitor_events record failed: %s", exc)
            return

        if random.random() < 0.02:
            DemoVisitorService.cleanup_old_events()

    @staticmethod
    def cleanup_old_events() -> None:
        if not DemoVisitorService.is_enabled():
            return
        cutoff = (get_moscow_now() - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM demo_visitor_events WHERE created_at < ?", (cutoff,))
                conn.commit()
        except Exception as exc:
            logger.debug("demo_visitor_events cleanup failed: %s", exc)

    @staticmethod
    def online_count() -> int:
        if not DemoVisitorService.is_enabled():
            return 0
        cutoff = (get_moscow_now() - timedelta(minutes=ONLINE_WINDOW_MINUTES)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    SELECT COUNT(DISTINCT {_SESSION_KEY_SQL}) AS c
                    FROM demo_visitor_events
                    WHERE event_type IN ('login', 'heartbeat')
                      AND created_at >= ?
                    """,
                    (cutoff,),
                )
                row = cur.fetchone()
                if row is None:
                    return 0
                return int(row["c"] if hasattr(row, "keys") else row[0] or 0)
        except Exception as exc:
            logger.debug("demo_visitor online_count failed: %s", exc)
            return 0

    @staticmethod
    def _today_bounds() -> tuple[str, str]:
        now = get_moscow_now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def resolve_period_bounds(
        period: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Пресеты MSK: today | yesterday | day_before_yesterday | days_3 | week | month | custom.
        Диапазон clamp к RETENTION_DAYS. Возвращает start/end строки и метаданные для UI.
        """
        from datetime import datetime

        now = get_moscow_now()
        if getattr(now, "tzinfo", None) is not None:
            now = now.replace(tzinfo=None)
        today0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
        retention_start = today0 - timedelta(days=RETENTION_DAYS - 1)
        period = (period or "today").strip().lower()
        labels = {
            "today": "Сегодня",
            "yesterday": "Вчера",
            "day_before_yesterday": "Позавчера",
            "days_3": "3 дня назад",
            "week": "7 дней",
            "month": "30 дней",
            "custom": "Произвольный период",
        }
        if period not in labels:
            period = "today"

        end = now
        if period == "today":
            start = today0
        elif period == "yesterday":
            start = today0 - timedelta(days=1)
            end = today0 - timedelta(microseconds=1)
        elif period == "day_before_yesterday":
            start = today0 - timedelta(days=2)
            end = today0 - timedelta(days=1, microseconds=1)
        elif period == "days_3":
            start = today0 - timedelta(days=3)
            end = today0 - timedelta(days=2, microseconds=1)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = max(now - timedelta(days=30), retention_start)
        elif period == "custom":
            def _parse_day(s: Optional[str]):
                if not s:
                    return None
                try:
                    d = datetime.strptime(s.strip()[:10], "%Y-%m-%d")
                    return d
                except ValueError:
                    return None

            start_p = _parse_day(date_from)
            end_p = _parse_day(date_to)
            if start_p is None and end_p is None:
                period = "today"
                start = today0
                end = now
            else:
                start = start_p if start_p else retention_start
                end = (
                    end_p.replace(hour=23, minute=59, second=59)
                    if end_p
                    else now
                )
                if start > end:
                    start, end = (
                        end.replace(hour=0, minute=0, second=0, microsecond=0),
                        start.replace(hour=23, minute=59, second=59),
                    )
        else:
            start = today0

        if start < retention_start:
            start = retention_start
        if end > now:
            end = now
        if start > end:
            start = end.replace(hour=0, minute=0, second=0, microsecond=0)

        multi_day = (end.date() - start.date()).days >= 1

        return {
            "period": period,
            "period_label": labels.get(period, period),
            "start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end.strftime("%Y-%m-%d %H:%M:%S"),
            "date_from": start.strftime("%Y-%m-%d"),
            "date_to": end.strftime("%Y-%m-%d"),
            "multi_day": multi_day,
            "retention_days": RETENTION_DAYS,
        }

    @staticmethod
    def stats_for_range(
        period: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        bounds = DemoVisitorService.resolve_period_bounds(period, date_from, date_to)
        empty = {
            "online": 0,
            "logins_today": 0,
            "unique_users_today": 0,
            "unique_sessions_today": 0,
            "unique_ips_today": 0,
            "events_today": 0,
            "top_users": [],
            "top_ips": [],
            "by_hour": [],
            "by_day": [],
            "chart_mode": "hour",
            "online_window_minutes": ONLINE_WINDOW_MINUTES,
            **bounds,
        }
        if not DemoVisitorService.is_enabled():
            return empty

        range_start = bounds["start"]
        range_end = bounds["end"]
        multi_day = bool(bounds["multi_day"])
        online = DemoVisitorService.online_count()
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()

                def _count(row) -> int:
                    if row is None:
                        return 0
                    if hasattr(row, "keys"):
                        return int(row["c"] or 0)
                    return int(row[0] or 0)

                cur.execute(
                    """
                    SELECT COUNT(*) AS c FROM demo_visitor_events
                    WHERE event_type = 'login'
                      AND created_at >= ? AND created_at <= ?
                    """,
                    (range_start, range_end),
                )
                logins = _count(cur.fetchone())

                cur.execute(
                    """
                    SELECT COUNT(DISTINCT user_id) AS c FROM demo_visitor_events
                    WHERE user_id IS NOT NULL
                      AND event_type IN ('login', 'heartbeat')
                      AND created_at >= ? AND created_at <= ?
                    """,
                    (range_start, range_end),
                )
                unique_users = _count(cur.fetchone())

                cur.execute(
                    f"""
                    SELECT COUNT(DISTINCT {_SESSION_KEY_SQL}) AS c
                    FROM demo_visitor_events
                    WHERE event_type IN ('login', 'heartbeat')
                      AND created_at >= ? AND created_at <= ?
                    """,
                    (range_start, range_end),
                )
                unique_sessions = _count(cur.fetchone())

                cur.execute(
                    """
                    SELECT COUNT(DISTINCT ip) AS c FROM demo_visitor_events
                    WHERE ip IS NOT NULL AND ip != ''
                      AND created_at >= ? AND created_at <= ?
                    """,
                    (range_start, range_end),
                )
                unique_ips = _count(cur.fetchone())

                cur.execute(
                    """
                    SELECT COUNT(*) AS c FROM demo_visitor_events
                    WHERE created_at >= ? AND created_at <= ?
                    """,
                    (range_start, range_end),
                )
                events_count = _count(cur.fetchone())

                cur.execute(
                    """
                    SELECT COALESCE(username, '(unknown)') AS username,
                           COUNT(*) AS cnt
                    FROM demo_visitor_events
                    WHERE event_type IN ('login', 'heartbeat')
                      AND created_at >= ? AND created_at <= ?
                    GROUP BY COALESCE(username, '(unknown)')
                    ORDER BY cnt DESC
                    LIMIT 15
                    """,
                    (range_start, range_end),
                )
                top_users = [
                    {
                        "username": r[0] if not hasattr(r, "keys") else r["username"],
                        "count": int(r[1] if not hasattr(r, "keys") else r["cnt"]),
                    }
                    for r in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT COALESCE(ip, '(unknown)') AS ip,
                           COUNT(*) AS cnt
                    FROM demo_visitor_events
                    WHERE created_at >= ? AND created_at <= ?
                    GROUP BY COALESCE(ip, '(unknown)')
                    ORDER BY cnt DESC
                    LIMIT 15
                    """,
                    (range_start, range_end),
                )
                top_ips = [
                    {
                        "ip": r[0] if not hasattr(r, "keys") else r["ip"],
                        "count": int(r[1] if not hasattr(r, "keys") else r["cnt"]),
                    }
                    for r in cur.fetchall()
                ]

                by_hour: List[Dict[str, Any]] = []
                by_day: List[Dict[str, Any]] = []
                chart_mode = "day" if multi_day else "hour"
                if multi_day:
                    cur.execute(
                        """
                        SELECT to_char(created_at, 'YYYY-MM-DD') AS day,
                               COUNT(*) AS cnt
                        FROM demo_visitor_events
                        WHERE event_type IN ('login', 'heartbeat')
                          AND created_at >= ? AND created_at <= ?
                        GROUP BY to_char(created_at, 'YYYY-MM-DD')
                        ORDER BY day
                        """,
                        (range_start, range_end),
                    )
                    day_map = {
                        (r[0] if not hasattr(r, "keys") else r["day"]): int(
                            r[1] if not hasattr(r, "keys") else r["cnt"]
                        )
                        for r in cur.fetchall()
                    }
                    from datetime import datetime as _dt

                    d0 = _dt.strptime(bounds["date_from"], "%Y-%m-%d").date()
                    d1 = _dt.strptime(bounds["date_to"], "%Y-%m-%d").date()
                    cur_d = d0
                    while cur_d <= d1:
                        key = cur_d.strftime("%Y-%m-%d")
                        by_day.append({"day": key, "count": int(day_map.get(key, 0))})
                        cur_d = cur_d + timedelta(days=1)
                else:
                    cur.execute(
                        """
                        SELECT to_char(created_at, 'HH24') AS hour,
                               COUNT(*) AS cnt
                        FROM demo_visitor_events
                        WHERE event_type IN ('login', 'heartbeat')
                          AND created_at >= ? AND created_at <= ?
                        GROUP BY to_char(created_at, 'HH24')
                        ORDER BY hour
                        """,
                        (range_start, range_end),
                    )
                    hour_map = {
                        (r[0] if not hasattr(r, "keys") else r["hour"]): int(
                            r[1] if not hasattr(r, "keys") else r["cnt"]
                        )
                        for r in cur.fetchall()
                    }
                    by_hour = [
                        {"hour": f"{h:02d}", "count": int(hour_map.get(f"{h:02d}", 0))}
                        for h in range(24)
                    ]

            return {
                "online": online,
                "logins_today": logins,
                "unique_users_today": unique_users,
                "unique_sessions_today": unique_sessions,
                "unique_ips_today": unique_ips,
                "events_today": events_count,
                "top_users": top_users,
                "top_ips": top_ips,
                "by_hour": by_hour,
                "by_day": by_day,
                "chart_mode": chart_mode,
                "online_window_minutes": ONLINE_WINDOW_MINUTES,
                "as_of": get_moscow_now_str(),
                **bounds,
            }
        except Exception as exc:
            logger.warning("demo_visitor stats_for_range failed: %s", exc)
            empty["online"] = online
            return empty

    @staticmethod
    def stats_today() -> Dict[str, Any]:
        return DemoVisitorService.stats_for_range("today")

    @staticmethod
    def recent_sessions(
        limit: int = 50,
        range_start: Optional[str] = None,
        range_end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not DemoVisitorService.is_enabled():
            return []
        limit = max(1, min(int(limit or 50), 200))
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                if range_start and range_end:
                    cur.execute(
                        """
                        SELECT id, user_id, username, ip, user_agent, path, event_type,
                               created_at, client_instance_id
                        FROM demo_visitor_events
                        WHERE created_at >= ? AND created_at <= ?
                        ORDER BY created_at DESC, id DESC
                        LIMIT ?
                        """,
                        (range_start, range_end, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, user_id, username, ip, user_agent, path, event_type,
                               created_at, client_instance_id
                        FROM demo_visitor_events
                        ORDER BY created_at DESC, id DESC
                        LIMIT ?
                        """,
                        (limit,),
                    )
                rows = cur.fetchall()
                result = []
                for r in rows:
                    if hasattr(r, "keys"):
                        result.append(
                            {
                                "id": r["id"],
                                "user_id": r["user_id"],
                                "username": r["username"],
                                "ip": r["ip"],
                                "user_agent": r["user_agent"],
                                "path": r["path"],
                                "event_type": r["event_type"],
                                "created_at": r["created_at"],
                                "client_instance_id": r["client_instance_id"],
                            }
                        )
                    else:
                        result.append(
                            {
                                "id": r[0],
                                "user_id": r[1],
                                "username": r[2],
                                "ip": r[3],
                                "user_agent": r[4],
                                "path": r[5],
                                "event_type": r[6],
                                "created_at": r[7],
                                "client_instance_id": r[8] if len(r) > 8 else None,
                            }
                        )
                return result
        except Exception as exc:
            logger.debug("demo_visitor recent_sessions failed: %s", exc)
            return []

    @staticmethod
    def online_users(limit: int = 50) -> List[Dict[str, Any]]:
        """Кто сейчас онлайн — по экземпляру браузера (не по user_id)."""
        if not DemoVisitorService.is_enabled():
            return []
        cutoff = (get_moscow_now() - timedelta(minutes=ONLINE_WINDOW_MINUTES)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        limit = max(1, min(int(limit or 50), 200))
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    SELECT e.user_id, e.username, e.ip, e.path, e.created_at,
                           e.client_instance_id, e.user_agent,
                           {_SESSION_KEY_SQL_E} AS session_key
                    FROM demo_visitor_events e
                    INNER JOIN (
                        SELECT {_SESSION_KEY_SQL} AS sk, MAX(created_at) AS max_created
                        FROM demo_visitor_events
                        WHERE event_type IN ('login', 'heartbeat')
                          AND created_at >= ?
                        GROUP BY {_SESSION_KEY_SQL}
                    ) t ON {_SESSION_KEY_SQL_E} = t.sk AND e.created_at = t.max_created
                    WHERE e.event_type IN ('login', 'heartbeat')
                      AND e.created_at >= ?
                    ORDER BY e.created_at DESC
                    LIMIT ?
                    """,
                    (cutoff, cutoff, limit),
                )

                rows = cur.fetchall()
                out = []
                for r in rows:
                    if hasattr(r, "keys"):
                        ua = r["user_agent"] or ""
                        out.append(
                            {
                                "user_id": r["user_id"],
                                "username": r["username"],
                                "ip": r["ip"],
                                "path": r["path"],
                                "last_seen": r["created_at"],
                                "client_instance_id": r["client_instance_id"],
                                "browser": (ua[:60] + "…") if len(ua) > 60 else ua,
                            }
                        )
                    else:
                        ua = r[6] or ""
                        out.append(
                            {
                                "user_id": r[0],
                                "username": r[1],
                                "ip": r[2],
                                "path": r[3],
                                "last_seen": r[4],
                                "client_instance_id": r[5],
                                "browser": (ua[:60] + "…") if len(ua) > 60 else ua,
                            }
                        )
                return out
        except Exception as exc:
            logger.debug("demo_visitor online_users failed: %s", exc)
            return []
