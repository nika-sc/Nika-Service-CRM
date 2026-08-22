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


def sniff_client_upload(header: bytes, filename: str) -> Optional[str]:
    """
    Разрешённые вложения диагностики: jpeg/png/pdf.
    Возвращает серверный MIME или None, если тип не совпал с содержимым.
    """
    return sniff_staff_upload(header, filename, allow=("jpg", "jpeg", "png", "pdf"))


def sniff_staff_upload(
    header: bytes,
    filename: str,
    allow: Optional[frozenset] = None,
) -> Optional[str]:
    """
    Magic-bytes check for staff uploads (comments, chat, invoice assets).
    Extension must match sniffed content.
    """
    if is_forbidden_upload_extension(filename):
        return None
    ext = file_extension(filename)
    if allow is not None and ext not in allow:
        return None
    data = header or b""
    if ext in ("jpg", "jpeg") and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if ext == "png" and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if ext == "gif" and data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if ext == "webp" and len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if ext == "bmp" and data[:2] == b"BM":
        return "image/bmp"
    if ext == "pdf" and data[:5] == b"%PDF-":
        return "application/pdf"
    if ext in ("zip", "docx", "xlsx") and data[:4] == b"PK\x03\x04":
        return mime_from_filename(filename)
    if ext in ("doc", "xls") and data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return mime_from_filename(filename)
    if ext == "rar" and data[:4] == b"Rar!":
        return "application/x-rar-compressed"
    if ext == "7z" and data[:6] == b"7z\xbc\xaf'\x1c":
        return "application/x-7z-compressed"
    if ext in ("txt", "csv"):
        sample = data[:4096]
        if b"\x00" in sample:
            return None
        return "text/plain" if ext == "txt" else "text/csv"
    return None


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
