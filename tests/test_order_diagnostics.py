"""ACL, limits and close-gate for order diagnostics."""
from io import BytesIO

import pytest

from app.services.order_diagnostics_service import (
    MAX_FILE_SIZE,
    MAX_FILES_PER_ORDER,
    OrderDiagnosticsService,
)
from app.utils.exceptions import ValidationError


def test_diagnostics_limits():
    assert MAX_FILE_SIZE == 5 * 1024 * 1024
    assert MAX_FILES_PER_ORDER == 10


def test_diagnostics_access_matrix():
    compute = OrderDiagnosticsService.compute_access

    open_empty = compute(
        is_admin=False, can_edit_orders=True, order_locked=False, text_set=False
    )
    assert open_empty["can_edit_text"] is True
    assert open_empty["can_upload"] is True
    assert open_empty["can_delete_files"] is False

    open_written = compute(
        is_admin=False, can_edit_orders=True, order_locked=False, text_set=True
    )
    assert open_written["can_edit_text"] is False
    assert open_written["can_upload"] is True
    assert open_written["can_delete_files"] is False

    locked_staff = compute(
        is_admin=False, can_edit_orders=True, order_locked=True, text_set=True
    )
    assert locked_staff["can_edit_text"] is False
    assert locked_staff["can_upload"] is False
    assert locked_staff["can_delete_files"] is False

    locked_admin = compute(
        is_admin=True, can_edit_orders=True, order_locked=True, text_set=True
    )
    assert locked_admin["can_edit_text"] is True
    assert locked_admin["can_upload"] is True
    assert locked_admin["can_delete_files"] is True

    viewer = compute(
        is_admin=False, can_edit_orders=False, order_locked=False, text_set=False
    )
    assert viewer["can_edit_text"] is False
    assert viewer["can_upload"] is False
    assert viewer["can_delete_files"] is False


def test_closing_blocked_without_diagnostics_text():
    msg = OrderDiagnosticsService.closing_blocked_message
    assert msg(True, False, "") == "Сначала заполните диагностику"
    assert msg(False, True, "   ") == "Сначала заполните диагностику"
    assert msg(True, True, None) == "Сначала заполните диагностику"
    assert msg(True, True, "плата не держит заряд") is None
    assert msg(False, False, "") is None


class _MemFile:
    def __init__(self, name, data):
        self.filename = name
        self._buf = BytesIO(data)

    def seek(self, off, whence=0):
        return self._buf.seek(off, whence)

    def tell(self):
        return self._buf.tell()

    def read(self, n=-1):
        return self._buf.read(n)

    def save(self, path):
        with open(path, "wb") as fh:
            fh.write(self._buf.getvalue())


def test_diagnostics_file_rejects_over_5mb():
    payload = b"\xff\xd8\xff" + (b"x" * (MAX_FILE_SIZE + 8))
    with pytest.raises(ValidationError, match="5 МБ"):
        OrderDiagnosticsService.save_file(
            1, _MemFile("photo.jpg", payload), user_id=1, can_edit_orders=True
        )


def test_save_text_writes_history_and_action_log():
    import inspect

    src = inspect.getsource(OrderDiagnosticsService.save_text)
    assert "order_diagnostics_history" in src
    assert "_log" in src
    log_src = inspect.getsource(OrderDiagnosticsService._log)
    assert "ActionLogService" in log_src
    assert "add_diagnostics_file" in inspect.getsource(OrderDiagnosticsService.save_file)
    assert "delete_diagnostics_file" in inspect.getsource(OrderDiagnosticsService.delete_file)
    assert "require_on_disk=False" in inspect.getsource(OrderDiagnosticsService.delete_file)
    save_src = inspect.getsource(OrderDiagnosticsService.save_file)
    assert "stored_name" in save_src
    assert "file_storage.save(confined)" in save_src


def test_resolve_client_file_path_relative_and_legacy_absolute(tmp_path, monkeypatch):
    from app.services import order_diagnostics_service as diag

    upload_dir = tmp_path / "order_client"
    upload_dir.mkdir()
    monkeypatch.setattr(diag, "UPLOAD_DIR", str(upload_dir))
    body = b"hello"
    rel = "abc123_photo.jpg"
    (upload_dir / rel).write_bytes(body)
    assert diag.resolve_client_file_path(rel).endswith(rel)
    legacy = str(upload_dir / rel)
    assert diag.resolve_client_file_path(legacy) == str((upload_dir / rel).resolve())
    missing = diag.resolve_client_file_path("no-such.jpg")
    assert missing is None or not __import__("os").path.exists(missing)


def test_docker_compose_persists_app_uploads():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    nginx_conf = (root / "nginx" / "nginx.conf").read_text(encoding="utf-8")
    assert "location /static/uploads/invoices/" in nginx_conf
    assert "alias /var/www/nika/uploads/;" not in nginx_conf

    found_compose = False
    for compose_path in (root / "docker" / "docker-compose.yml", root / "docker-compose.yml"):
        if not compose_path.is_file():
            continue
        text = compose_path.read_text(encoding="utf-8")
        if "include:" in text and ":/app/uploads" not in text:
            continue
        found_compose = True
        assert ":/app/uploads" in text
        assert "uploads/invoices:/app/static/uploads/invoices" in text
        assert "uploads/invoices:/var/www/nika/uploads/invoices" in text
    assert found_compose

    entry = root / "docker" / "docker-entrypoint.sh"
    if not entry.is_file():
        entry = root / "docker-entrypoint.sh"
    assert "uploads/order_client" in entry.read_text(encoding="utf-8")
