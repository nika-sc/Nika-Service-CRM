"""Проверка, что путь к файлу остаётся внутри каталога загрузок."""
from __future__ import annotations

import os
from typing import Optional


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
