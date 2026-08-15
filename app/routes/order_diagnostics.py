"""Staff API: диагностика заявки и вложения для ЛК."""
from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user

from app.services.order_diagnostics_service import OrderDiagnosticsService
from app.services.user_service import UserService
from app.utils.error_handlers import api_internal_error
from app.utils.exceptions import NotFoundError, PermissionError, ValidationError
from app.utils.safe_files import mime_from_filename

bp = Blueprint("order_diagnostics", __name__, url_prefix="/api/order")


def _require(perm: str):
    if not UserService.check_permission(current_user.id, perm):
        return jsonify({"success": False, "error": "Недостаточно прав"}), 403
    return None


def _actor():
    role = getattr(current_user, "role", "") or ""
    return {
        "user_id": current_user.id,
        "username": getattr(current_user, "username", None),
        "is_admin": role.strip().lower() == "admin",
        "can_edit_orders": UserService.check_permission(current_user.id, "edit_orders"),
    }


@bp.route("/<int:order_id>/diagnostics", methods=["GET"])
@login_required
def get_diagnostics(order_id):
    denied = _require("view_orders")
    if denied:
        return denied
    try:
        actor = _actor()
        payload = OrderDiagnosticsService.get_payload(
            order_id,
            is_admin=actor["is_admin"],
            can_edit_orders=actor["can_edit_orders"],
        )
        return jsonify({"success": True, **payload})
    except NotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return api_internal_error(e)


@bp.route("/<int:order_id>/diagnostics", methods=["PUT"])
@login_required
def save_diagnostics(order_id):
    denied = _require("edit_orders")
    if denied:
        return denied
    try:
        actor = _actor()
        data = request.get_json(silent=True) or {}
        OrderDiagnosticsService.save_text(
            order_id,
            data.get("diagnostics") or "",
            user_id=actor["user_id"],
            username=actor["username"],
            is_admin=actor["is_admin"],
            can_edit_orders=actor["can_edit_orders"],
        )
        return jsonify({"success": True})
    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except ValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return api_internal_error(e)


@bp.route("/<int:order_id>/diagnostics/files", methods=["POST"])
@login_required
def upload_diagnostics_file(order_id):
    denied = _require("edit_orders")
    if denied:
        return denied
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "Файл не загружен"}), 400
        actor = _actor()
        saved = OrderDiagnosticsService.save_file(
            order_id,
            request.files["file"],
            actor["user_id"],
            username=actor["username"],
            is_admin=actor["is_admin"],
            can_edit_orders=actor["can_edit_orders"],
        )
        return jsonify({"success": True, "file": saved}), 201
    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except ValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except NotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return api_internal_error(e)


@bp.route("/<int:order_id>/diagnostics/files/<int:file_id>", methods=["GET"])
@login_required
def download_diagnostics_file(order_id, file_id):
    denied = _require("view_orders")
    if denied:
        return denied
    try:
        info = OrderDiagnosticsService.get_file_for_order(order_id, file_id)
        inline = (info["mime_type"] or "").startswith("image/")
        resp = send_file(
            info["abs_path"],
            mimetype=mime_from_filename(info["filename"]),
            as_attachment=not inline,
            download_name=info["filename"],
        )
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Content-Disposition"] = (
            ("inline" if inline else "attachment")
            + f'; filename="{info["filename"]}"'
        )
        return resp
    except NotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return api_internal_error(e)


@bp.route("/<int:order_id>/diagnostics/files/<int:file_id>", methods=["DELETE"])
@login_required
def delete_diagnostics_file(order_id, file_id):
    denied = _require("edit_orders")
    if denied:
        return denied
    try:
        actor = _actor()
        OrderDiagnosticsService.delete_file(
            order_id,
            file_id,
            user_id=actor["user_id"],
            username=actor["username"],
            is_admin=actor["is_admin"],
            can_edit_orders=actor["can_edit_orders"],
        )
        return jsonify({"success": True})
    except PermissionError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    except NotFoundError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return api_internal_error(e)
