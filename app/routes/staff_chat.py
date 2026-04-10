"""
Blueprint и websocket-обработчики внутреннего чата сотрудников.
"""
import logging
import os

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user, login_required

from app.services.staff_chat_service import StaffChatService, StaffChatValidationError

logger = logging.getLogger(__name__)

bp = Blueprint("staff_chat", __name__, url_prefix="/api/staff-chat")
CHAT_NAMESPACE = "/staff-chat"
GLOBAL_ROOM_KEY = "global"


def _can_use_staff_chat() -> bool:
    if not getattr(current_user, "is_authenticated", False):
        return False
    role = str(getattr(current_user, "role", "") or "").strip().lower()
    if role in {"manager", "master", "admin"}:
        return True
    try:
        from app.services.user_service import UserService
        permission_candidates = (
            "view_orders",
            "create_orders",
            "edit_orders",
            "view_finance",
            "manage_finance",
            "view_warehouse",
            "manage_warehouse",
            "manage_shop",
            "salary.view",
        )
        return any(UserService.check_permission(current_user.id, p) for p in permission_candidates)
    except Exception:
        return False


def _socket_room(room_key: str) -> str:
    room = (room_key or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
    return f"staff_chat:{room}"


def emit_staff_chat_message(message: dict):
    """Публикует сообщение в websocket-комнату (если сокеты доступны)."""
    room_key = (message.get("room_key") or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
    socketio = current_app.extensions.get("socketio")
    if not socketio:
        return
    socketio.emit(
        "message_created",
        {"message": message},
        namespace=CHAT_NAMESPACE,
        room=_socket_room(room_key),
    )


def emit_staff_chat_message_updated(message: dict):
    room_key = (message.get("room_key") or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
    socketio = current_app.extensions.get("socketio")
    if not socketio:
        return
    socketio.emit(
        "message_updated",
        {"message": message},
        namespace=CHAT_NAMESPACE,
        room=_socket_room(room_key),
    )


def emit_staff_chat_message_deleted(message_id: int, room_key: str = GLOBAL_ROOM_KEY):
    socketio = current_app.extensions.get("socketio")
    if not socketio:
        return
    socketio.emit(
        "message_deleted",
        {"message_id": int(message_id)},
        namespace=CHAT_NAMESPACE,
        room=_socket_room(room_key),
    )


def emit_staff_chat_reactions_updated(message: dict):
    room_key = (message.get("room_key") or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
    socketio = current_app.extensions.get("socketio")
    if not socketio:
        return
    socketio.emit(
        "message_updated",
        {"message": message},
        namespace=CHAT_NAMESPACE,
        room=_socket_room(room_key),
    )


@bp.route("/history", methods=["GET"])
@login_required
def api_staff_chat_history():
    if not _can_use_staff_chat():
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403
    try:
        limit = request.args.get("limit", default=40, type=int)
        before_id = request.args.get("before_id", default=None, type=int)
        room_key = (request.args.get("room_key") or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
        messages = StaffChatService.get_history(
            room_key=room_key,
            before_id=before_id,
            limit=limit,
            current_user_id=current_user.id,
            actor_display_name=request.args.get("actor_display_name"),
            client_instance_id=request.args.get("client_instance_id"),
        )
        return jsonify({"success": True, "messages": messages, "limits": StaffChatService.get_limits()})
    except Exception as e:
        logger.error("Ошибка получения истории чата: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "Не удалось получить историю"}), 500


@bp.route("/send", methods=["POST"])
@login_required
def api_staff_chat_send_message():
    if not _can_use_staff_chat():
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403
    try:
        data = request.get_json(silent=True) or {}
        message = StaffChatService.create_message(
            user_id=current_user.id,
            username=current_user.username,
            actor_display_name=data.get("actor_display_name"),
            client_instance_id=data.get("client_instance_id"),
            message_text=data.get("message_text"),
            room_key=data.get("room_key") or GLOBAL_ROOM_KEY,
        )
        emit_staff_chat_message(message)
        return jsonify({"success": True, "message": message}), 201
    except StaffChatValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("Ошибка отправки сообщения: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "Не удалось отправить сообщение"}), 500


@bp.route("/upload", methods=["POST"])
@login_required
def api_staff_chat_upload():
    if not _can_use_staff_chat():
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403
    try:
        files = request.files.getlist("files")
        room_key = (request.form.get("room_key") or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
        message = StaffChatService.create_message_with_files(
            user_id=current_user.id,
            username=current_user.username,
            actor_display_name=request.form.get("actor_display_name"),
            client_instance_id=request.form.get("client_instance_id"),
            message_text=request.form.get("message_text"),
            files=files,
            room_key=room_key,
        )
        emit_staff_chat_message(message)
        return jsonify({"success": True, "message": message}), 201
    except StaffChatValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("Ошибка загрузки файлов чата: %s", e, exc_info=True)
        return jsonify({"success": False, "error": "Не удалось загрузить файл"}), 500


@bp.route("/message/<int:message_id>", methods=["PATCH"])
@login_required
def api_staff_chat_edit(message_id: int):
    if not _can_use_staff_chat():
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403
    try:
        data = request.get_json(silent=True) or {}
        message = StaffChatService.update_message(
            message_id=message_id,
            user_id=current_user.id,
            actor_display_name=data.get("actor_display_name"),
            client_instance_id=data.get("client_instance_id"),
            message_text=data.get("message_text"),
        )
        emit_staff_chat_message_updated(message)
        return jsonify({"success": True, "message": message})
    except StaffChatValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("Ошибка редактирования сообщения %s: %s", message_id, e, exc_info=True)
        return jsonify({"success": False, "error": "Не удалось отредактировать сообщение"}), 500


@bp.route("/message/<int:message_id>", methods=["DELETE"])
@login_required
def api_staff_chat_delete(message_id: int):
    if not _can_use_staff_chat():
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403
    try:
        data = request.get_json(silent=True) or {}
        ok = StaffChatService.delete_message(
            message_id=message_id,
            user_id=current_user.id,
            actor_display_name=data.get("actor_display_name"),
            client_instance_id=data.get("client_instance_id"),
        )
        if not ok:
            return jsonify({"success": False, "error": "Сообщение не найдено"}), 404
        emit_staff_chat_message_deleted(message_id, room_key=GLOBAL_ROOM_KEY)
        return jsonify({"success": True})
    except StaffChatValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("Ошибка удаления сообщения %s: %s", message_id, e, exc_info=True)
        return jsonify({"success": False, "error": "Не удалось удалить сообщение"}), 500


@bp.route("/message/<int:message_id>/reaction", methods=["POST"])
@login_required
def api_staff_chat_toggle_reaction(message_id: int):
    if not _can_use_staff_chat():
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403
    try:
        data = request.get_json(silent=True) or {}
        message = StaffChatService.toggle_reaction(
            message_id=message_id,
            user_id=current_user.id,
            username=current_user.username,
            actor_display_name=data.get("actor_display_name"),
            client_instance_id=data.get("client_instance_id"),
            emoji=data.get("emoji"),
        )
        emit_staff_chat_reactions_updated(message)
        return jsonify({"success": True, "message": message})
    except StaffChatValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error("Ошибка реакции на сообщение %s: %s", message_id, e, exc_info=True)
        return jsonify({"success": False, "error": "Не удалось применить реакцию"}), 500


@bp.route("/file/<int:attachment_id>", methods=["GET"])
@login_required
def api_staff_chat_get_file(attachment_id: int):
    if not _can_use_staff_chat():
        return jsonify({"success": False, "error": "Доступ запрещен"}), 403
    try:
        item = StaffChatService.get_attachment(attachment_id)
        if not item:
            return jsonify({"success": False, "error": "Файл не найден"}), 404
        path = item["abs_path"]
        if not os.path.exists(path):
            return jsonify({"success": False, "error": "Файл не найден на диске"}), 404
        return send_file(
            path,
            mimetype=item["mime_type"] or "application/octet-stream",
            as_attachment=False,
            download_name=item["original_name"],
        )
    except Exception as e:
        logger.error("Ошибка выдачи файла чата %s: %s", attachment_id, e, exc_info=True)
        return jsonify({"success": False, "error": "Не удалось открыть файл"}), 500


def init_staff_chat_socketio(socketio):
    """Регистрирует websocket-обработчики staff chat."""
    if not socketio:
        return
    try:
        from flask_socketio import emit, join_room
    except Exception:
        logger.warning("SocketIO недоступен, staff chat websocket обработчики не активированы")
        return

    @socketio.on("connect", namespace=CHAT_NAMESPACE)
    def on_connect():
        if not _can_use_staff_chat():
            return False
        join_room(_socket_room(GLOBAL_ROOM_KEY))
        emit("chat_connected", {"success": True, "room_key": GLOBAL_ROOM_KEY})
        return True

    @socketio.on("join_room", namespace=CHAT_NAMESPACE)
    def on_join_room(payload):
        if not _can_use_staff_chat():
            emit("chat_error", {"error": "Доступ запрещен"})
            return
        data = payload or {}
        room_key = (data.get("room_key") or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
        join_room(_socket_room(room_key))
        emit("room_joined", {"room_key": room_key})

    @socketio.on("send_message", namespace=CHAT_NAMESPACE)
    def on_send_message(payload):
        if not _can_use_staff_chat():
            emit("chat_error", {"error": "Доступ запрещен"})
            return
        data = payload or {}
        try:
            room_key = (data.get("room_key") or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
            message = StaffChatService.create_message(
                user_id=current_user.id,
                username=current_user.username,
                actor_display_name=data.get("actor_display_name"),
                client_instance_id=data.get("client_instance_id"),
                message_text=data.get("message_text"),
                room_key=room_key,
            )
            emit("message_created", {"message": message}, room=_socket_room(room_key))
        except StaffChatValidationError as e:
            emit("chat_error", {"error": str(e)})
        except Exception as e:
            logger.error("Ошибка websocket отправки сообщения: %s", e, exc_info=True)
            emit("chat_error", {"error": "Не удалось отправить сообщение"})

    @socketio.on("edit_message", namespace=CHAT_NAMESPACE)
    def on_edit_message(payload):
        if not _can_use_staff_chat():
            emit("chat_error", {"error": "Доступ запрещен"})
            return
        data = payload or {}
        try:
            message_id = int(data.get("message_id") or 0)
            message = StaffChatService.update_message(
                message_id=message_id,
                user_id=current_user.id,
                actor_display_name=data.get("actor_display_name"),
                client_instance_id=data.get("client_instance_id"),
                message_text=data.get("message_text"),
            )
            emit("message_updated", {"message": message}, room=_socket_room(message.get("room_key") or GLOBAL_ROOM_KEY))
        except StaffChatValidationError as e:
            emit("chat_error", {"error": str(e)})
        except Exception as e:
            logger.error("Ошибка websocket редактирования сообщения: %s", e, exc_info=True)
            emit("chat_error", {"error": "Не удалось отредактировать сообщение"})

    @socketio.on("delete_message", namespace=CHAT_NAMESPACE)
    def on_delete_message(payload):
        if not _can_use_staff_chat():
            emit("chat_error", {"error": "Доступ запрещен"})
            return
        data = payload or {}
        try:
            message_id = int(data.get("message_id") or 0)
            ok = StaffChatService.delete_message(
                message_id=message_id,
                user_id=current_user.id,
                actor_display_name=data.get("actor_display_name"),
                client_instance_id=data.get("client_instance_id"),
            )
            if not ok:
                emit("chat_error", {"error": "Сообщение не найдено"})
                return
            emit("message_deleted", {"message_id": message_id}, room=_socket_room(GLOBAL_ROOM_KEY))
        except StaffChatValidationError as e:
            emit("chat_error", {"error": str(e)})
        except Exception as e:
            logger.error("Ошибка websocket удаления сообщения: %s", e, exc_info=True)
            emit("chat_error", {"error": "Не удалось удалить сообщение"})

    @socketio.on("typing", namespace=CHAT_NAMESPACE)
    def on_typing(payload):
        if not _can_use_staff_chat():
            return
        data = payload or {}
        room_key = (data.get("room_key") or GLOBAL_ROOM_KEY).strip() or GLOBAL_ROOM_KEY
        actor_name = str(data.get("actor_display_name") or "").strip()
        client_instance_id = str(data.get("client_instance_id") or "").strip()
        is_typing = bool(data.get("is_typing"))
        emit(
            "typing",
            {
                "actor_display_name": actor_name,
                "client_instance_id": client_instance_id,
                "is_typing": is_typing,
            },
            room=_socket_room(room_key),
            include_self=False,
        )

    @socketio.on("toggle_reaction", namespace=CHAT_NAMESPACE)
    def on_toggle_reaction(payload):
        if not _can_use_staff_chat():
            emit("chat_error", {"error": "Доступ запрещен"})
            return
        data = payload or {}
        try:
            message_id = int(data.get("message_id") or 0)
            message = StaffChatService.toggle_reaction(
                message_id=message_id,
                user_id=current_user.id,
                username=current_user.username,
                actor_display_name=data.get("actor_display_name"),
                client_instance_id=data.get("client_instance_id"),
                emoji=data.get("emoji"),
            )
            emit("message_updated", {"message": message}, room=_socket_room(message.get("room_key") or GLOBAL_ROOM_KEY))
        except StaffChatValidationError as e:
            emit("chat_error", {"error": str(e)})
        except Exception as e:
            logger.error("Ошибка websocket реакции на сообщение: %s", e, exc_info=True)
            emit("chat_error", {"error": "Не удалось применить реакцию"})
