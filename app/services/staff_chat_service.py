"""
Сервис внутреннего чата сотрудников.
"""
import logging
import mimetypes
import os
import sqlite3
import uuid
from typing import Dict, List, Optional

import bleach
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.database.connection import get_db_connection
from app.utils.datetime_utils import get_moscow_now

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_UPLOAD_ROOT = os.path.join(_PROJECT_ROOT, "data", "uploads", "staff_chat")
_MAX_FILE_SIZE_BYTES = int(os.environ.get("STAFF_CHAT_MAX_FILE_SIZE_MB", "20")) * 1024 * 1024
_MAX_FILES_PER_MESSAGE = int(os.environ.get("STAFF_CHAT_MAX_FILES_PER_MESSAGE", "8"))
_MAX_MESSAGE_LENGTH = int(os.environ.get("STAFF_CHAT_MAX_MESSAGE_LENGTH", "4000"))
_MAX_ACTOR_NAME_LENGTH = 120
_MAX_CLIENT_INSTANCE_LENGTH = 200
_DEFAULT_ROOM_KEY = "global"
_ALLOWED_REACTIONS = {"👍", "❤️", "😂", "😮", "😢", "🔥", "✅", "👀"}

_ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "bmp",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "txt",
    "csv",
    "zip",
    "rar",
    "7z",
}
_ALLOWED_MIME_PREFIXES = ("image/", "text/")
_ALLOWED_MIME_EXACT = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "application/x-rar-compressed",
    "application/x-7z-compressed",
}


class StaffChatValidationError(ValueError):
    """Ошибки валидации входных данных чата."""


def _is_allowed_file(filename: str, mime_type: str) -> bool:
    ext = ""
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()
    if ext in _ALLOWED_EXTENSIONS:
        return True
    if not mime_type:
        return False
    if mime_type in _ALLOWED_MIME_EXACT:
        return True
    return any(mime_type.startswith(prefix) for prefix in _ALLOWED_MIME_PREFIXES)


def _sanitize_text(text: Optional[str]) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    # Храним только plain text, чтобы исключить XSS при рендере.
    value = bleach.clean(value, tags=[], attributes={}, strip=True)
    if len(value) > _MAX_MESSAGE_LENGTH:
        raise StaffChatValidationError(
            f"Сообщение слишком длинное (максимум {_MAX_MESSAGE_LENGTH} символов)"
        )
    return value


def _sanitize_actor_name(name: Optional[str]) -> str:
    value = bleach.clean((name or "").strip(), tags=[], attributes={}, strip=True)
    if len(value) > _MAX_ACTOR_NAME_LENGTH:
        value = value[:_MAX_ACTOR_NAME_LENGTH]
    return value


def _sanitize_client_instance_id(client_instance_id: Optional[str]) -> str:
    value = (client_instance_id or "").strip()
    if len(value) > _MAX_CLIENT_INSTANCE_LENGTH:
        value = value[:_MAX_CLIENT_INSTANCE_LENGTH]
    return value


def _sanitize_reaction_emoji(emoji: Optional[str]) -> str:
    value = (emoji or "").strip()
    if value not in _ALLOWED_REACTIONS:
        raise StaffChatValidationError("Недопустимая реакция")
    return value


def _serialize_message_row(row) -> Dict:
    return {
        "id": row["id"],
        "room_key": row["room_key"],
        "user_id": row["user_id"],
        "username": row["username"],
        "actor_display_name": row["actor_display_name"] or "",
        "client_instance_id": row["client_instance_id"] or "",
        "message_text": row["message_text"] or "",
        "created_at": str(row["created_at"]) if row["created_at"] is not None else None,
        "edited_at": str(row["edited_at"]) if row["edited_at"] is not None else None,
        "deleted_at": str(row["deleted_at"]) if row["deleted_at"] is not None else None,
        "attachments": [],
        "reactions": [],
    }


def _serialize_attachment_row(row) -> Dict:
    return {
        "id": row["id"],
        "original_name": row["original_name"],
        "stored_name": row["stored_name"],
        "mime_type": row["mime_type"] or "",
        "size_bytes": int(row["size_bytes"] or 0),
        "is_image": bool(row["is_image"]),
        "created_at": str(row["created_at"]) if row["created_at"] is not None else None,
        "url": f"/api/staff-chat/file/{row['id']}",
    }


class StaffChatService:
    """Сервисный слой работы с сообщениями и вложениями чата."""

    @staticmethod
    def _is_missing_reactions_table_error(exc: Exception) -> bool:
        msg = str(exc or "").lower()
        # Postgres: relation "staff_chat_reactions" does not exist
        # SQLite: no such table: staff_chat_reactions
        return "staff_chat_reactions" in msg and (
            "does not exist" in msg
            or "не существует" in msg
            or "no such table" in msg
        )

    @staticmethod
    def _attach_reactions(
        cursor,
        messages: List[Dict],
        *,
        current_user_id: Optional[int],
        actor_display_name: Optional[str],
        client_instance_id: Optional[str],
    ) -> None:
        if not messages:
            return
        actor = _sanitize_actor_name(actor_display_name)
        client_id = _sanitize_client_instance_id(client_instance_id)
        ids = [int(m["id"]) for m in messages]
        placeholders = ",".join(["?"] * len(ids))
        try:
            cursor.execute(
                f"""
                SELECT
                    message_id,
                    emoji,
                    COUNT(*) AS reaction_count,
                    SUM(
                        CASE
                            WHEN user_id = ?
                             AND actor_display_name = ?
                             AND client_instance_id = ?
                            THEN 1 ELSE 0
                        END
                    ) AS mine_count
                FROM staff_chat_reactions
                WHERE message_id IN ({placeholders})
                GROUP BY message_id, emoji
                ORDER BY message_id ASC, emoji ASC
                """,
                [current_user_id, actor, client_id, *ids],
            )
        except Exception as e:
            if StaffChatService._is_missing_reactions_table_error(e):
                logger.warning("Таблица staff_chat_reactions не найдена: реакции временно отключены до миграции")
                for message in messages:
                    message["reactions"] = []
                return
            raise
        by_message: Dict[int, List[Dict]] = {}
        for row in cursor.fetchall():
            by_message.setdefault(int(row["message_id"]), []).append(
                {
                    "emoji": row["emoji"],
                    "count": int(row["reaction_count"] or 0),
                    "reacted_by_me": bool(int(row["mine_count"] or 0) > 0),
                }
            )
        for message in messages:
            message["reactions"] = by_message.get(int(message["id"]), [])

    @staticmethod
    def create_message(
        *,
        user_id: Optional[int],
        username: str,
        actor_display_name: Optional[str],
        client_instance_id: Optional[str],
        message_text: Optional[str],
        room_key: str = _DEFAULT_ROOM_KEY,
    ) -> Dict:
        clean_text = _sanitize_text(message_text)
        if not clean_text:
            raise StaffChatValidationError("Введите сообщение")

        actor_name = _sanitize_actor_name(actor_display_name)
        client_id = _sanitize_client_instance_id(client_instance_id)
        username = (username or "").strip() or "unknown"
        room = (room_key or _DEFAULT_ROOM_KEY).strip() or _DEFAULT_ROOM_KEY

        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO staff_chat_messages (
                    room_key, user_id, username, actor_display_name,
                    client_instance_id, message_text, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    room,
                    user_id,
                    username,
                    actor_name,
                    client_id,
                    clean_text,
                    get_moscow_now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            message_id = cursor.lastrowid
            conn.commit()

        message = StaffChatService.get_message_by_id(message_id)
        if not message:
            raise RuntimeError("Не удалось получить созданное сообщение")
        return message

    @staticmethod
    def create_message_with_files(
        *,
        user_id: Optional[int],
        username: str,
        actor_display_name: Optional[str],
        client_instance_id: Optional[str],
        message_text: Optional[str],
        files: List[FileStorage],
        room_key: str = _DEFAULT_ROOM_KEY,
    ) -> Dict:
        actor_name = _sanitize_actor_name(actor_display_name)
        client_id = _sanitize_client_instance_id(client_instance_id)
        clean_text = _sanitize_text(message_text)
        username = (username or "").strip() or "unknown"
        room = (room_key or _DEFAULT_ROOM_KEY).strip() or _DEFAULT_ROOM_KEY

        valid_files = [f for f in (files or []) if f and getattr(f, "filename", "")]
        if len(valid_files) > _MAX_FILES_PER_MESSAGE:
            raise StaffChatValidationError(
                f"Можно загрузить не более {_MAX_FILES_PER_MESSAGE} файлов за раз"
            )
        if not clean_text and not valid_files:
            raise StaffChatValidationError("Введите сообщение или приложите файл")

        now = get_moscow_now()
        target_dir = os.path.join(_UPLOAD_ROOT, now.strftime("%Y"), now.strftime("%m"))
        os.makedirs(target_dir, exist_ok=True)

        attachments_to_insert = []
        for file_obj in valid_files:
            original_name = os.path.basename((file_obj.filename or "").strip())
            if not original_name:
                continue
            mime_type = (file_obj.mimetype or "").strip().lower()
            if not _is_allowed_file(original_name, mime_type):
                raise StaffChatValidationError(f"Недопустимый тип файла: {original_name}")

            file_obj.stream.seek(0, os.SEEK_END)
            file_size = file_obj.stream.tell()
            file_obj.stream.seek(0)
            if file_size > _MAX_FILE_SIZE_BYTES:
                max_mb = int(_MAX_FILE_SIZE_BYTES / (1024 * 1024))
                raise StaffChatValidationError(f"Файл {original_name} слишком большой (до {max_mb} MB)")

            safe_name = secure_filename(original_name) or "file"
            ext = ""
            if "." in safe_name:
                ext = "." + safe_name.rsplit(".", 1)[1].lower()
            stored_name = f"{uuid.uuid4().hex}{ext}"
            abs_path = os.path.join(target_dir, stored_name)
            rel_path = os.path.relpath(abs_path, _PROJECT_ROOT).replace("\\", "/")
            file_obj.save(abs_path)
            if not mime_type:
                guessed, _ = mimetypes.guess_type(original_name)
                mime_type = guessed or "application/octet-stream"
            attachments_to_insert.append(
                {
                    "original_name": original_name,
                    "stored_name": stored_name,
                    "mime_type": mime_type or "application/octet-stream",
                    "size_bytes": int(file_size),
                    "file_path": rel_path,
                    "is_image": 1 if (mime_type or "").startswith("image/") else 0,
                }
            )

        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO staff_chat_messages (
                    room_key, user_id, username, actor_display_name,
                    client_instance_id, message_text, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    room,
                    user_id,
                    username,
                    actor_name,
                    client_id,
                    clean_text,
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            message_id = cursor.lastrowid

            for a in attachments_to_insert:
                cursor.execute(
                    """
                    INSERT INTO staff_chat_attachments (
                        message_id, original_name, stored_name, mime_type,
                        size_bytes, file_path, is_image, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        a["original_name"],
                        a["stored_name"],
                        a["mime_type"],
                        a["size_bytes"],
                        a["file_path"],
                        a["is_image"],
                        now.strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
            conn.commit()

        message = StaffChatService.get_message_by_id(message_id)
        if not message:
            raise RuntimeError("Не удалось получить созданное сообщение")
        return message

    @staticmethod
    def get_message_by_id(
        message_id: int,
        *,
        current_user_id: Optional[int] = None,
        actor_display_name: Optional[str] = None,
        client_instance_id: Optional[str] = None,
    ) -> Optional[Dict]:
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, room_key, user_id, username, actor_display_name,
                       client_instance_id, message_text, created_at, edited_at, deleted_at
                FROM staff_chat_messages
                WHERE id = ?
                LIMIT 1
                """,
                (message_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            msg = _serialize_message_row(row)
            cursor.execute(
                """
                SELECT id, message_id, original_name, stored_name, mime_type,
                       size_bytes, file_path, is_image, created_at
                FROM staff_chat_attachments
                WHERE message_id = ?
                ORDER BY id ASC
                """,
                (message_id,),
            )
            msg["attachments"] = [_serialize_attachment_row(a) for a in cursor.fetchall()]
            StaffChatService._attach_reactions(
                cursor,
                [msg],
                current_user_id=current_user_id,
                actor_display_name=actor_display_name,
                client_instance_id=client_instance_id,
            )
            return msg

    @staticmethod
    def get_history(
        *,
        room_key: str = _DEFAULT_ROOM_KEY,
        before_id: Optional[int] = None,
        limit: int = 40,
        current_user_id: Optional[int] = None,
        actor_display_name: Optional[str] = None,
        client_instance_id: Optional[str] = None,
    ) -> List[Dict]:
        safe_limit = max(1, min(int(limit or 40), 100))
        room = (room_key or _DEFAULT_ROOM_KEY).strip() or _DEFAULT_ROOM_KEY

        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            if before_id:
                cursor.execute(
                    """
                    SELECT id, room_key, user_id, username, actor_display_name,
                           client_instance_id, message_text, created_at, edited_at, deleted_at
                    FROM staff_chat_messages
                    WHERE room_key = ?
                      AND deleted_at IS NULL
                      AND id < ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (room, int(before_id), safe_limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, room_key, user_id, username, actor_display_name,
                           client_instance_id, message_text, created_at, edited_at, deleted_at
                    FROM staff_chat_messages
                    WHERE room_key = ?
                      AND deleted_at IS NULL
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (room, safe_limit),
                )
            rows = cursor.fetchall()
            rows = list(reversed(rows))
            if not rows:
                return []

            messages = [_serialize_message_row(row) for row in rows]
            ids = [m["id"] for m in messages]
            placeholders = ",".join(["?"] * len(ids))
            cursor.execute(
                f"""
                SELECT id, message_id, original_name, stored_name, mime_type,
                       size_bytes, file_path, is_image, created_at
                FROM staff_chat_attachments
                WHERE message_id IN ({placeholders})
                ORDER BY message_id ASC, id ASC
                """,
                ids,
            )
            attachments_map: Dict[int, List[Dict]] = {}
            for row in cursor.fetchall():
                msg_id = row["message_id"]
                attachments_map.setdefault(msg_id, []).append(_serialize_attachment_row(row))
            for message in messages:
                message["attachments"] = attachments_map.get(message["id"], [])
            StaffChatService._attach_reactions(
                cursor,
                messages,
                current_user_id=current_user_id,
                actor_display_name=actor_display_name,
                client_instance_id=client_instance_id,
            )
            return messages

    @staticmethod
    def get_attachment(attachment_id: int) -> Optional[Dict]:
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT a.id, a.message_id, a.original_name, a.stored_name, a.mime_type,
                       a.size_bytes, a.file_path, a.is_image, a.created_at,
                       m.room_key, m.deleted_at
                FROM staff_chat_attachments a
                JOIN staff_chat_messages m ON m.id = a.message_id
                WHERE a.id = ?
                LIMIT 1
                """,
                (attachment_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if row["deleted_at"] is not None:
                return None
            rel_path = (row["file_path"] or "").replace("\\", "/")
            abs_path = os.path.join(_PROJECT_ROOT, rel_path)
            return {
                "id": row["id"],
                "message_id": row["message_id"],
                "original_name": row["original_name"],
                "mime_type": row["mime_type"] or "application/octet-stream",
                "size_bytes": int(row["size_bytes"] or 0),
                "is_image": bool(row["is_image"]),
                "room_key": row["room_key"] or _DEFAULT_ROOM_KEY,
                "file_path": rel_path,
                "abs_path": abs_path,
            }

    @staticmethod
    def get_limits() -> Dict[str, int]:
        return {
            "max_file_size_bytes": _MAX_FILE_SIZE_BYTES,
            "max_files_per_message": _MAX_FILES_PER_MESSAGE,
            "max_message_length": _MAX_MESSAGE_LENGTH,
        }

    @staticmethod
    def _message_owned_by_actor(*, message_id: int, user_id: Optional[int], actor_display_name: Optional[str], client_instance_id: Optional[str]) -> bool:
        actor = _sanitize_actor_name(actor_display_name)
        client_id = _sanitize_client_instance_id(client_instance_id)
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id
                FROM staff_chat_messages
                WHERE id = ?
                  AND deleted_at IS NULL
                  AND user_id = ?
                  AND COALESCE(actor_display_name, '') = ?
                  AND COALESCE(client_instance_id, '') = ?
                LIMIT 1
                """,
                (message_id, user_id, actor, client_id),
            )
            return cursor.fetchone() is not None

    @staticmethod
    def update_message(
        *,
        message_id: int,
        user_id: Optional[int],
        actor_display_name: Optional[str],
        client_instance_id: Optional[str],
        message_text: Optional[str],
    ) -> Dict:
        clean_text = _sanitize_text(message_text)
        if not clean_text:
            raise StaffChatValidationError("Введите текст сообщения")
        if not StaffChatService._message_owned_by_actor(
            message_id=message_id,
            user_id=user_id,
            actor_display_name=actor_display_name,
            client_instance_id=client_instance_id,
        ):
            raise StaffChatValidationError("Можно редактировать только свои сообщения с этого ПК")
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE staff_chat_messages
                SET message_text = ?, edited_at = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (clean_text, get_moscow_now().strftime("%Y-%m-%d %H:%M:%S"), message_id),
            )
            conn.commit()
        msg = StaffChatService.get_message_by_id(message_id)
        if not msg:
            raise StaffChatValidationError("Сообщение не найдено")
        return msg

    @staticmethod
    def delete_message(
        *,
        message_id: int,
        user_id: Optional[int],
        actor_display_name: Optional[str],
        client_instance_id: Optional[str],
    ) -> bool:
        if not StaffChatService._message_owned_by_actor(
            message_id=message_id,
            user_id=user_id,
            actor_display_name=actor_display_name,
            client_instance_id=client_instance_id,
        ):
            raise StaffChatValidationError("Можно удалять только свои сообщения с этого ПК")
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE staff_chat_messages
                SET deleted_at = ?, message_text = ''
                WHERE id = ? AND deleted_at IS NULL
                """,
                (get_moscow_now().strftime("%Y-%m-%d %H:%M:%S"), message_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def toggle_reaction(
        *,
        message_id: int,
        user_id: Optional[int],
        username: str,
        actor_display_name: Optional[str],
        client_instance_id: Optional[str],
        emoji: Optional[str],
    ) -> Dict:
        clean_emoji = _sanitize_reaction_emoji(emoji)
        actor = _sanitize_actor_name(actor_display_name)
        client_id = _sanitize_client_instance_id(client_instance_id)
        username = (username or "").strip() or "unknown"

        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id
                FROM staff_chat_messages
                WHERE id = ? AND deleted_at IS NULL
                LIMIT 1
                """,
                (message_id,),
            )
            if not cursor.fetchone():
                raise StaffChatValidationError("Сообщение не найдено")

            try:
                cursor.execute(
                    """
                    SELECT id
                    FROM staff_chat_reactions
                    WHERE message_id = ?
                      AND user_id = ?
                      AND actor_display_name = ?
                      AND client_instance_id = ?
                      AND emoji = ?
                    LIMIT 1
                    """,
                    (message_id, user_id, actor, client_id, clean_emoji),
                )
            except Exception as e:
                if StaffChatService._is_missing_reactions_table_error(e):
                    raise StaffChatValidationError(
                        "Реакции станут доступны после применения миграций БД"
                    ) from e
                raise
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "DELETE FROM staff_chat_reactions WHERE id = ?",
                    (existing["id"],),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO staff_chat_reactions (
                        message_id, user_id, username, actor_display_name,
                        client_instance_id, emoji, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        user_id,
                        username,
                        actor,
                        client_id,
                        clean_emoji,
                        get_moscow_now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
            conn.commit()

        msg = StaffChatService.get_message_by_id(
            message_id,
            current_user_id=user_id,
            actor_display_name=actor,
            client_instance_id=client_id,
        )
        if not msg:
            raise StaffChatValidationError("Сообщение не найдено")
        return msg
