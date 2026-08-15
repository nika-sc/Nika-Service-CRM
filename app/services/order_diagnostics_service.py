"""Диагностика заявки и клиентские вложения (jpeg/png/pdf)."""
from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from typing import Any, Optional

from werkzeug.utils import secure_filename

from app.database.connection import get_db_connection
from app.utils.exceptions import NotFoundError, PermissionError, ValidationError
from app.utils.safe_files import confined_file_path, mime_from_filename, sniff_client_upload

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(_PROJECT_ROOT, "uploads", "order_client")
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_FILES_PER_ORDER = 10
ALLOWED_EXT = frozenset({"jpg", "jpeg", "png", "pdf"})
_LOG_CLIP = 500


def _clip(text: Optional[str], n: int = _LOG_CLIP) -> str:
    body = text or ""
    if len(body) <= n:
        return body
    return body[:n] + "…"


class OrderDiagnosticsService:
    @staticmethod
    def compute_access(
        *,
        is_admin: bool,
        can_edit_orders: bool,
        order_locked: bool,
        text_set: bool,
    ) -> dict[str, bool]:
        """Матрица прав на диагностику (без обращения к БД)."""
        staff_write = bool(is_admin or can_edit_orders)
        return {
            "can_edit_text": bool(is_admin or (staff_write and not order_locked and not text_set)),
            "can_upload": bool(is_admin or (staff_write and not order_locked)),
            "can_delete_files": bool(is_admin),
            "order_locked": bool(order_locked),
            "text_set": bool(text_set),
            "is_admin": bool(is_admin),
        }

    @staticmethod
    def closing_blocked_message(
        blocks_edit: bool,
        is_final: bool,
        diagnostics_text: Optional[str],
    ) -> Optional[str]:
        """Текст ошибки, если в блокирующий статус нельзя без диагностики."""
        if not (blocks_edit or is_final):
            return None
        if (diagnostics_text or "").strip():
            return None
        return "Сначала заполните диагностику"

    @staticmethod
    def _deny_edit_text(access: dict[str, bool]) -> str:
        if access.get("order_locked") and not access.get("is_admin"):
            return "На закрытой заявке диагностику может изменить только администратор"
        if access.get("text_set") and not access.get("is_admin"):
            return "Только администратор может изменить сохранённую диагностику"
        return "Недостаточно прав"

    @staticmethod
    def _deny_upload(access: dict[str, bool]) -> str:
        if access.get("order_locked") and not access.get("is_admin"):
            return "На закрытой заявке файлы может загрузить только администратор"
        return "Недостаточно прав"

    @staticmethod
    def _load_state(cursor, order_id: int) -> dict[str, Any]:
        cursor.execute(
            """
            SELECT o.diagnostics, os.blocks_edit, os.is_final
            FROM orders AS o
            LEFT JOIN order_statuses AS os ON os.id = o.status_id
            WHERE o.id = ?
            """,
            (order_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise NotFoundError("Заявка не найдена")
        diagnostics = (row["diagnostics"] or "") if row["diagnostics"] is not None else ""
        blocks_edit = bool(row["blocks_edit"]) if row["blocks_edit"] is not None else False
        is_final = bool(row["is_final"]) if row["is_final"] is not None else False
        return {
            "diagnostics": diagnostics,
            "order_locked": blocks_edit or is_final,
            "text_set": bool(diagnostics.strip()),
        }

    @staticmethod
    def get_access(
        order_id: int,
        *,
        is_admin: bool = False,
        can_edit_orders: bool = False,
    ) -> dict[str, bool]:
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            state = OrderDiagnosticsService._load_state(cursor, order_id)
        return OrderDiagnosticsService.compute_access(
            is_admin=is_admin,
            can_edit_orders=can_edit_orders,
            order_locked=state["order_locked"],
            text_set=state["text_set"],
        )

    @staticmethod
    def get_payload(
        order_id: int,
        *,
        is_admin: bool = False,
        can_edit_orders: bool = False,
    ) -> dict[str, Any]:
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            state = OrderDiagnosticsService._load_state(cursor, order_id)
            cursor.execute(
                """
                SELECT id, filename, file_size, mime_type, created_at
                FROM order_client_files
                WHERE order_id = ?
                ORDER BY id ASC
                """,
                (order_id,),
            )
            files = []
            for r in cursor.fetchall():
                item = dict(r)
                if item.get("created_at") is not None:
                    item["created_at"] = str(item["created_at"])
                files.append(item)
            cursor.execute(
                """
                SELECT h.id, h.body, h.created_at, h.created_by,
                       COALESCE(NULLIF(TRIM(u.display_name), ''), u.username) AS author
                FROM order_diagnostics_history AS h
                LEFT JOIN users AS u ON u.id = h.created_by
                WHERE h.order_id = ?
                ORDER BY h.id DESC
                """,
                (order_id,),
            )
            history = []
            for r in cursor.fetchall():
                item = dict(r)
                if item.get("created_at") is not None:
                    item["created_at"] = str(item["created_at"])
                history.append(item)
        access = OrderDiagnosticsService.compute_access(
            is_admin=is_admin,
            can_edit_orders=can_edit_orders,
            order_locked=state["order_locked"],
            text_set=state["text_set"],
        )
        return {
            "order_id": order_id,
            "diagnostics": state["diagnostics"] or "",
            "files": files,
            "history": history,
            **access,
        }

    @staticmethod
    def save_text(
        order_id: int,
        text: str,
        *,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        is_admin: bool = False,
        can_edit_orders: bool = False,
    ) -> None:
        body = (text or "").strip()
        if len(body) > 8000:
            raise ValidationError("Текст диагностики слишком длинный")
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            state = OrderDiagnosticsService._load_state(cursor, order_id)
            access = OrderDiagnosticsService.compute_access(
                is_admin=is_admin,
                can_edit_orders=can_edit_orders,
                order_locked=state["order_locked"],
                text_set=state["text_set"],
            )
            if not access["can_edit_text"]:
                raise PermissionError(OrderDiagnosticsService._deny_edit_text(access))
            old = state["diagnostics"] or ""
            if old == body:
                return
            from app.utils.datetime_utils import get_moscow_now_str

            now = get_moscow_now_str()
            cursor.execute(
                """
                INSERT INTO order_diagnostics_history (order_id, body, created_by, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, body, user_id, now),
            )
            cursor.execute(
                "UPDATE orders SET diagnostics = ? WHERE id = ?",
                (body, order_id),
            )
            conn.commit()
        OrderDiagnosticsService._log(
            user_id=user_id,
            username=username,
            action_type="update",
            description="Изменена диагностика заявки",
            details={
                "field": "diagnostics",
                "old": _clip(old),
                "new": _clip(body),
            },
            entity_id=order_id,
        )

    @staticmethod
    def save_file(
        order_id: int,
        file_storage,
        user_id: Optional[int],
        *,
        username: Optional[str] = None,
        is_admin: bool = False,
        can_edit_orders: bool = False,
    ) -> dict[str, Any]:
        filename = secure_filename(getattr(file_storage, "filename", "") or "")
        if not filename:
            raise ValidationError("Файл не выбран")
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXT:
            raise ValidationError("Разрешены только JPEG, PNG и PDF")

        file_storage.seek(0, os.SEEK_END)
        size = file_storage.tell()
        file_storage.seek(0)
        if size <= 0:
            raise ValidationError("Пустой файл")
        if size > MAX_FILE_SIZE:
            raise ValidationError("Файл больше 5 МБ")

        header = file_storage.read(16)
        file_storage.seek(0)
        sniffed = sniff_client_upload(header, filename)
        if not sniffed:
            raise ValidationError("Содержимое файла не совпадает с расширением")

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        stored_name = f"{uuid.uuid4().hex}_{filename}"
        abs_path = os.path.join(UPLOAD_DIR, stored_name)
        confined = confined_file_path(abs_path, UPLOAD_DIR)
        if not confined:
            raise ValidationError("Недопустимый путь файла")

        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            state = OrderDiagnosticsService._load_state(cursor, order_id)
            access = OrderDiagnosticsService.compute_access(
                is_admin=is_admin,
                can_edit_orders=can_edit_orders,
                order_locked=state["order_locked"],
                text_set=state["text_set"],
            )
            if not access["can_upload"]:
                raise PermissionError(OrderDiagnosticsService._deny_upload(access))
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM order_client_files WHERE order_id = ?",
                (order_id,),
            )
            count_row = cursor.fetchone()
            count = int(count_row["cnt"] if count_row else 0)
            if count >= MAX_FILES_PER_ORDER:
                raise ValidationError("Не больше 10 файлов на заявку")

            file_storage.save(confined)
            stored_mime = mime_from_filename(filename)
            cursor.execute(
                """
                INSERT INTO order_client_files
                    (order_id, filename, file_path, file_size, mime_type, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (order_id, filename, confined, size, stored_mime, user_id),
            )
            conn.commit()
            file_id = cursor.lastrowid

        OrderDiagnosticsService._log(
            user_id=user_id,
            username=username,
            action_type="add_diagnostics_file",
            description=f"Добавлен файл диагностики: {filename}",
            details={"filename": filename, "file_size": size, "file_id": file_id},
            entity_id=order_id,
        )
        return {
            "id": file_id,
            "filename": filename,
            "file_size": size,
            "mime_type": stored_mime,
        }

    @staticmethod
    def get_file_for_order(order_id: int, file_id: int) -> dict[str, Any]:
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, order_id, filename, file_path, file_size, mime_type
                FROM order_client_files
                WHERE id = ? AND order_id = ?
                """,
                (file_id, order_id),
            )
            row = cursor.fetchone()
        if not row:
            raise NotFoundError("Файл не найден")
        path = confined_file_path(row["file_path"], UPLOAD_DIR)
        if not path or not os.path.exists(path):
            raise NotFoundError("Файл не найден на диске")
        data = dict(row)
        data["abs_path"] = path
        return data

    @staticmethod
    def delete_file(
        order_id: int,
        file_id: int,
        *,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        is_admin: bool = False,
        can_edit_orders: bool = False,
    ) -> None:
        access = OrderDiagnosticsService.get_access(
            order_id, is_admin=is_admin, can_edit_orders=can_edit_orders
        )
        if not access["can_delete_files"]:
            raise PermissionError("Удалять фото диагностики может только администратор")
        info = OrderDiagnosticsService.get_file_for_order(order_id, file_id)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM order_client_files WHERE id = ? AND order_id = ?",
                (file_id, order_id),
            )
            conn.commit()
        try:
            os.remove(info["abs_path"])
        except OSError:
            logger.debug("could not remove diagnostics file %s", info.get("abs_path"))
        OrderDiagnosticsService._log(
            user_id=user_id,
            username=username,
            action_type="delete_diagnostics_file",
            description=f"Удалён файл диагностики: {info.get('filename')}",
            details={
                "filename": info.get("filename"),
                "file_size": info.get("file_size"),
                "file_id": file_id,
            },
            entity_id=order_id,
        )

    @staticmethod
    def _log(
        *,
        user_id: Optional[int],
        username: Optional[str],
        action_type: str,
        description: str,
        details: dict[str, Any],
        entity_id: int,
    ) -> None:
        try:
            from app.services.action_log_service import ActionLogService

            ActionLogService.log_action(
                user_id=user_id,
                username=username,
                action_type=action_type,
                entity_type="order",
                entity_id=entity_id,
                description=description,
                details=details,
            )
        except Exception as e:
            logger.warning("Не удалось залогировать диагностику заявки #%s: %s", entity_id, e)
