#!/usr/bin/env python3
"""
Генерация пары VAPID-ключей для Web Push чата сотрудников (pywebpush).
Печатает строки STAFF_CHAT_VAPID_* для добавления в .env (ничего не записывает на диск).

Зависимость: pip install cryptography
(уже тянется вместе с pywebpush в requirements.txt)
"""
from __future__ import annotations

import argparse
import base64
import sys

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
except ImportError:
    print("Установите cryptography: pip install cryptography", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser(description="VAPID-ключи для STAFF_CHAT Web Push")
    p.add_argument(
        "--claim-email",
        default="mailto:admin@example.com",
        metavar="mailto:...",
        help='Значение STAFF_CHAT_VAPID_CLAIM_EMAIL (по умолчанию mailto:admin@example.com)',
    )
    args = p.parse_args()
    claim = (args.claim_email or "").strip()
    if claim and not claim.startswith("mailto:"):
        claim = f"mailto:{claim}"

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
    one_line = priv_pem.replace("\n", "\\n")

    print("Добавьте в .env (или переменные окружения / docker-compose env):\n")
    print(f"STAFF_CHAT_VAPID_PUBLIC_KEY={pub_b64}")
    print()
    print(f"STAFF_CHAT_VAPID_PRIVATE_KEY={one_line}")
    print()
    print(f"STAFF_CHAT_VAPID_CLAIM_EMAIL={claim}")
    print()
    print(
        "Далее: pip install pywebpush, миграции 061 (SQLite) / 008 (Postgres), "
        "в docker-compose проброс STAFF_CHAT_VAPID_* в сервис web."
    )


if __name__ == "__main__":
    main()
