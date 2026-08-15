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
