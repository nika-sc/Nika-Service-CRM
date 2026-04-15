#!/usr/bin/env python3
"""
Проверка дерева перед публикацией в OSS: явные признаки секретов / ключей.
Запуск: python scripts/check_oss_tree_guards.py <корень_дерева>
Выход 1 при нарушении.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Расширения и каталоги, где ищем текст
TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".html",
    ".js",
    ".css",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".env.example",
    ".sh",
    ".sql",
    ".txt",
}

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

# Не сканируем сам скрипт — в нём есть литералы паттернов.
SKIP_FILE_NAMES = frozenset({"check_oss_tree_guards.py"})

# Каталоги/префиксы, которые никогда не должны публиковаться в OSS.
FORBIDDEN_TOP_LEVEL_DIRS = frozenset({".cursor"})

# Реальные PEM-блоки (строка в файле), а не упоминание в тексте документации.
PEM_HEADER = re.compile(r"^-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.MULTILINE)

# Типичные паттерны, которые не должны оказываться в OSS
COMPILED = [
    re.compile(r"sk_live_[0-9a-zA-Z]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


def iter_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if rel.parts and rel.parts[0] in FORBIDDEN_TOP_LEVEL_DIRS:
            yield p, f"forbidden path ({rel.parts[0]})"
            continue
        if p.name in SKIP_FILE_NAMES:
            continue
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        name = p.name
        if name == ".env" or (name.startswith(".env") and name != ".env.example"):
            yield p, "forbidden path (env file)"
            continue
        suf = p.suffix.lower()
        if name == ".env.example" or suf in TEXT_SUFFIXES or name.endswith(".env.example"):
            yield p, None


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_oss_tree_guards.py <tree_root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    errors: list[str] = []
    for path, reason in iter_files(root):
        if reason:
            errors.append(f"{path.relative_to(root)}: {reason}")
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:4096]:
            continue
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            continue
        if PEM_HEADER.search(text):
            errors.append(f"{path.relative_to(root)}: PEM private key header detected")
        for rx in COMPILED:
            if rx.search(text):
                errors.append(f"{path.relative_to(root)}: matches {rx.pattern!r}")

    if errors:
        print("OSS guard failures:", file=sys.stderr)
        for e in errors[:50]:
            print(f"  {e}", file=sys.stderr)
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more", file=sys.stderr)
        return 1
    print("OSS tree guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
