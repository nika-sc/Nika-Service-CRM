"""
Web Push для чата сотрудников (VAPID). Доставка при новом сообщении, пока вкладка закрыта.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask

from app.database.connection import get_db_connection
from app.utils.datetime_utils import get_moscow_now

logger = logging.getLogger(__name__)

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover
    webpush = None  # type: ignore
    WebPushException = Exception  # type: ignore


def web_push_library_available() -> bool:
    return webpush is not None


def _is_missing_subscriptions_table(exc: Exception) -> bool:
    msg = str(exc or "").lower()
    return "staff_chat_web_push_subscriptions" in msg and (
        "does not exist" in msg
        or "не существует" in msg
        or "no such table" in msg
    )


class StaffChatWebPushService:
    @staticmethod
    def vapid_configured(app: Flask) -> Tuple[bool, str, str, str]:
        pub = (app.config.get("STAFF_CHAT_VAPID_PUBLIC_KEY") or "").strip()
        priv = (app.config.get("STAFF_CHAT_VAPID_PRIVATE_KEY") or "").strip()
        sub = (app.config.get("STAFF_CHAT_VAPID_CLAIM_EMAIL") or "mailto:noreply@localhost").strip()
        if not sub.startswith("mailto:"):
            sub = f"mailto:{sub}"
        if not pub or not priv:
            return False, "", "", sub
        return True, pub, priv, sub

    @staticmethod
    def upsert_subscription(
        *,
        user_id: int,
        subscription: Dict[str, Any],
        user_agent: str,
    ) -> None:
        endpoint = (subscription.get("endpoint") or "").strip()
        keys = subscription.get("keys") or {}
        p256dh = (keys.get("p256dh") or "").strip()
        auth = (keys.get("auth") or "").strip()
        if not endpoint or not p256dh or not auth:
            raise ValueError("Неполная подписка Push")

        now = get_moscow_now().strftime("%Y-%m-%d %H:%M:%S")
        ua = (user_agent or "")[:500]

        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO staff_chat_web_push_subscriptions (
                        user_id, endpoint, p256dh, auth, user_agent, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (user_id, endpoint) DO UPDATE SET
                        p256dh = excluded.p256dh,
                        auth = excluded.auth,
                        user_agent = excluded.user_agent,
                        updated_at = excluded.updated_at
                    """,
                    (user_id, endpoint, p256dh, auth, ua, now, now),
                )
            except Exception as e:
                if _is_missing_subscriptions_table(e):
                    logger.warning("Таблица staff_chat_web_push_subscriptions не найдена — пропуск подписки")
                    return
                raise
            conn.commit()

    @staticmethod
    def delete_subscription(*, user_id: int, endpoint: str) -> None:
        ep = (endpoint or "").strip()
        if not ep:
            return
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    DELETE FROM staff_chat_web_push_subscriptions
                    WHERE user_id = ? AND endpoint = ?
                    """,
                    (user_id, ep),
                )
            except Exception as e:
                if _is_missing_subscriptions_table(e):
                    return
                raise
            conn.commit()

    @staticmethod
    def list_subscriptions_except_user(exclude_user_id: int) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT user_id, endpoint, p256dh, auth
                    FROM staff_chat_web_push_subscriptions
                    WHERE user_id IS NOT NULL AND user_id != ?
                    """,
                    (int(exclude_user_id),),
                )
                for row in cursor.fetchall():
                    out.append(
                        {
                            "user_id": int(row["user_id"]),
                            "subscription": {
                                "endpoint": row["endpoint"],
                                "keys": {"p256dh": row["p256dh"], "auth": row["auth"]},
                            },
                        }
                    )
            except Exception as e:
                if _is_missing_subscriptions_table(e):
                    return []
                raise
        return out

    @staticmethod
    def schedule_notify_new_message(app: Flask, message: Dict[str, Any]) -> None:
        if webpush is None:
            return
        ok, _, _, _ = StaffChatWebPushService.vapid_configured(app)
        if not ok:
            return
        uid = message.get("user_id")
        if uid is None:
            return

        app_obj = app._get_current_object()

        def _run() -> None:
            with app_obj.app_context():
                StaffChatWebPushService._notify_new_message_sync(app_obj, message)

        threading.Thread(target=_run, name="staff-chat-webpush", daemon=True).start()

    @staticmethod
    def _notify_new_message_sync(app: Flask, message: Dict[str, Any]) -> None:
        if webpush is None:
            return
        ok, _pub, priv, claim_sub = StaffChatWebPushService.vapid_configured(app)
        if not ok:
            return
        sender_id = int(message.get("user_id") or 0)
        title = (message.get("actor_display_name") or message.get("username") or "Чат CRM").strip()
        body = (message.get("message_text") or "").replace("\r", " ").replace("\n", " ").strip()
        atts = message.get("attachments") or []
        if not body and isinstance(atts, list) and len(atts) > 0:
            body = f"Вложение: {(atts[0] or {}).get('original_name') or 'файл'}"
        if not body:
            body = "Новое сообщение"
        body = body[:220]
        mid = int(message.get("id") or 0)
        payload = {
            "title": title[:80],
            "body": body,
            "url": "/all_orders",
            "icon": "/static/favicon.svg",
            "tag": f"staff-chat-{mid}",
            "data": {"url": "/all_orders"},
        }
        data = json.dumps(payload, ensure_ascii=False)
        subs = StaffChatWebPushService.list_subscriptions_except_user(sender_id)
        if not subs:
            return

        for item in subs:
            sub = item.get("subscription")
            if not sub:
                continue
            try:
                webpush(
                    subscription_info=sub,
                    data=data,
                    vapid_private_key=priv,
                    vapid_claims={"sub": claim_sub},
                    ttl=86400,
                )
            except WebPushException as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status in (404, 410):
                    StaffChatWebPushService.delete_subscription(
                        user_id=int(item["user_id"]),
                        endpoint=str(sub.get("endpoint") or ""),
                    )
                logger.debug("WebPush skip/remove: %s", e)
            except Exception as e:
                logger.warning("WebPush ошибка: %s", e)
