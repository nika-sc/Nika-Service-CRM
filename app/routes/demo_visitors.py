"""
API и отчёт демо-статистики посещений (DEMO_VISITOR_STATS).
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify, render_template, request, abort
from flask_login import login_required, current_user

from app.services.demo_visitor_service import DemoVisitorService

bp = Blueprint("demo_visitors", __name__)
logger = logging.getLogger(__name__)


def _require_demo_stats_enabled():
    if not DemoVisitorService.is_enabled():
        abort(404)


@bp.route("/api/demo/online-count", methods=["GET"])
def api_online_count():
    """Публичный счётчик онлайн (без PII)."""
    _require_demo_stats_enabled()
    return jsonify({"online": DemoVisitorService.online_count()})


@bp.route("/api/demo/presence", methods=["POST"])
@login_required
def api_presence():
    """Heartbeat от браузера авторизованного пользователя."""
    _require_demo_stats_enabled()
    data = request.get_json(silent=True) or {}
    path = (data.get("path") or request.headers.get("Referer") or request.path or "")[:500]
    client_instance_id = data.get("client_instance_id") or request.form.get("client_instance_id")
    DemoVisitorService.record_event(
        event_type="heartbeat",
        user_id=getattr(current_user, "id", None),
        username=getattr(current_user, "username", None),
        path=path,
        client_instance_id=client_instance_id,
    )
    return jsonify({"ok": True, "online": DemoVisitorService.online_count()})


@bp.route("/reports/demo-visitors")
@login_required
def demo_visitors_report():
    """Расширенная статистика заходов — только admin на демо."""
    _require_demo_stats_enabled()
    role = (getattr(current_user, "role", None) or "").strip().lower()
    if role != "admin":
        abort(403)
    stats = DemoVisitorService.stats_today()
    recent = DemoVisitorService.recent_sessions(80)
    online_users = DemoVisitorService.online_users(50)
    return render_template(
        "reports/demo_visitors.html",
        stats=stats,
        recent=recent,
        online_users=online_users,
    )
