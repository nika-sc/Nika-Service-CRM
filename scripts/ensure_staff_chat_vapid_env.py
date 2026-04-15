#!/usr/bin/env python3
"""
Однократно дописывает STAFF_CHAT_VAPID_* в .env, если публичный ключ ещё не задан.
Запускать только на доверенной машине (создаёт/дополняет секреты).

Использование:
  python scripts/ensure_staff_chat_vapid_env.py
  python scripts/ensure_staff_chat_vapid_env.py /path/to/.env

Зависимость: pip install cryptography
"""
from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
except ImportError:
    print("Установите cryptography: pip install cryptography", file=sys.stderr)
    sys.exit(1)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _env_has_vapid_public(text: str) -> bool:
    return bool(re.search(r"^\s*STAFF_CHAT_VAPID_PUBLIC_KEY\s*=\s*\S+", text, re.MULTILINE))


def main() -> int:
    root = _repo_root()
    env_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / ".env"
    if not env_path.is_file():
        print(f"Нет файла {env_path} — создайте из .env.example", file=sys.stderr)
        return 1

    content = env_path.read_text(encoding="utf-8", errors="replace")
    if _env_has_vapid_public(content):
        print("STAFF_CHAT_VAPID_* уже заданы в .env — пропуск.")
        return 0

    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key()
    priv_pem = (
        priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        .decode("ascii")
        .strip()
    )
    pub_raw = pub.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = base64.urlsafe_b64encode(pub_raw).decode("ascii").rstrip("=")
    priv_one_line = priv_pem.replace("\n", "\\n")

    block = (
        "\n# Web Push (чат сотрудников), добавлено scripts/ensure_staff_chat_vapid_env.py\n"
        f"STAFF_CHAT_VAPID_PUBLIC_KEY={pub_b64}\n"
        f"STAFF_CHAT_VAPID_PRIVATE_KEY={priv_one_line}\n"
        "STAFF_CHAT_VAPID_CLAIM_EMAIL=mailto:noreply@localhost\n"
    )
    with open(env_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(block)
    print(f"В {env_path} добавлены STAFF_CHAT_VAPID_* (перезапустите приложение / контейнер web).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
