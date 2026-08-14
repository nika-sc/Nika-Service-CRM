"""Проверка, что путь к файлу остаётся внутри каталога загрузок."""
from __future__ import annotations

import mimetypes
import os
from typing import Optional

_FORBIDDEN_EXTENSIONS = frozenset({"svg", "svgz"})
_FORBIDDEN_MIMES = frozenset({"image/svg+xml"})


def file_extension(filename: str) -> str:
    """Расширение файла без точки, в нижнем регистре."""
    name = (filename or "").strip()
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[1].lower()


def mime_from_filename(filename: str, default: str = "application/octet-stream") -> str:
    """MIME только из расширения имени файла; SVG запрещён."""
    ext = file_extension(filename)
    if ext in _FORBIDDEN_EXTENSIONS:
        return default
    guessed, _ = mimetypes.guess_type(filename or "")
    mime = (guessed or default).lower()
    if mime in _FORBIDDEN_MIMES:
        return default
    return mime


def is_forbidden_upload_extension(filename: str) -> bool:
    ext = file_extension(filename)
    if ext in _FORBIDDEN_EXTENSIONS:
        return True
    return mime_from_filename(filename) in _FORBIDDEN_MIMES


def confined_file_path(path: Optional[str], root: Optional[str]) -> Optional[str]:
    """
    Канонический путь, только если он лежит внутри root.
    Иначе None (path traversal / путь вне uploads).
    """
    if not path or not root:
        return None
    try:
        root_real = os.path.normcase(os.path.realpath(root))
        candidate = path if os.path.isabs(path) else os.path.join(root, path)
        real = os.path.normcase(os.path.realpath(candidate))
    except (OSError, ValueError):
        return None
    if real == root_real or real.startswith(root_real + os.sep):
        return os.path.realpath(candidate)
    return None
