"""
Демо-заявка без боевых ФИО для скриншотов блога (диагностика + фото + оплата).

  python scripts/seed_blog_shot_order.py

Печатает customer_id и order_id. Не для продакшена.
"""
from __future__ import annotations

import os
import struct
import sys
import zlib
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

SHOT_PHONE = "79990000001"
SHOT_NAME = "Демо Клиент"
SHOT_EMAIL = "demo-shots@example.com"
DIAG_TEXT = (
    "Не включается после скачка напряжения. Питание в норме, "
    "заменена микросхема зарядки. Рекомендуем не использовать "
    "неоригинальный блок питания."
)


def _png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    raw = b""
    pixel = bytes(rgb)
    for _ in range(height):
        raw += b"\x00" + pixel * width

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


class _MemFile:
    def __init__(self, name: str, data: bytes):
        self.filename = name
        self._buf = BytesIO(data)

    def seek(self, off, whence=0):
        return self._buf.seek(off, whence)

    def tell(self):
        return self._buf.tell()

    def read(self, n=-1):
        return self._buf.read(n)

    def save(self, path):
        Path(path).write_bytes(self._buf.getvalue())


def main() -> int:
    os.chdir(ROOT)
    from app import create_app
    from app.database.connection import get_db_connection
    from app.models.customer import Customer
    from app.services.order_diagnostics_service import OrderDiagnosticsService
    from app.services.order_service import OrderService
    from app.services.payment_service import PaymentService
    from app.utils.validators import normalize_phone

    app = create_app()
    with app.app_context():
        phone = normalize_phone(SHOT_PHONE)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = ? LIMIT 1", ("admin",))
            row = cur.fetchone()
            if not row:
                print("Нет пользователя admin", file=sys.stderr)
                return 1
            admin_id = int(row[0] if not isinstance(row, dict) else row["id"])
            cur.execute("SELECT id FROM device_types ORDER BY id LIMIT 1")
            type_row = cur.fetchone()
            cur.execute("SELECT id FROM device_brands ORDER BY id LIMIT 1")
            brand_row = cur.fetchone()
            if not type_row or not brand_row:
                print("Нет справочника типов/брендов устройств", file=sys.stderr)
                return 1
            type_id = int(type_row[0] if not isinstance(type_row, dict) else type_row["id"])
            brand_id = int(brand_row[0] if not isinstance(brand_row, dict) else brand_row["id"])

        existing = Customer.get_by_phone(phone)
        order_id = None
        if existing:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id FROM orders WHERE customer_id = ? ORDER BY id DESC LIMIT 1",
                    (existing.id,),
                )
                found = cur.fetchone()
                if found:
                    order_id = int(found[0] if not isinstance(found, dict) else found["id"])
        if not order_id:
            created = OrderService.create_order(
                customer_name=SHOT_NAME,
                phone=phone,
                email=SHOT_EMAIL,
                device_type_id=type_id,
                device_brand_id=brand_id,
                manager_id=admin_id,
                master_id=admin_id,
                serial_number="SHOT-DEMO-001",
                prepayment="2500",
                prepayment_method="card",
                estimated_cost="4500",
                appearance="Корпус без сколов, комплект: устройство и кабель",
                comment="",
                symptom_tags="Не включается",
                model="DemoBook 14",
                user_id=admin_id,
            )
            order_id = int(created["id"])
        customer = Customer.get_by_phone(phone)
        customer_id = int(customer.id)

        payload = OrderDiagnosticsService.get_payload(
            order_id, is_admin=True, can_edit_orders=True
        )
        if not (payload.get("diagnostics") or "").strip():
            OrderDiagnosticsService.save_text(
                order_id,
                DIAG_TEXT,
                user_id=admin_id,
                username="admin",
                is_admin=True,
                can_edit_orders=True,
            )
        if not payload.get("files"):
            OrderDiagnosticsService.save_file(
                order_id,
                _MemFile("diagnostics-board.png", _png(320, 200, (43, 184, 166))),
                admin_id,
                username="admin",
                is_admin=True,
                can_edit_orders=True,
            )

        services = OrderService.get_order_services(order_id)
        if not services:
            OrderService.add_order_service(
                order_id,
                name="Диагностика и ремонт платы питания",
                price=4500.0,
                quantity=1,
            )

        try:
            PaymentService.add_payment(
                order_id,
                2000.0,
                "cash",
                user_id=admin_id,
                username="admin",
                comment="Доплата на выдаче",
                idempotency_key=f"shot-order-{order_id}-cash",
            )
        except Exception as exc:
            print("WARN payment:", exc)

        print(f"customer_id={customer_id}")
        print(f"order_id={order_id}")
        if existing:
            print("reused_phone=1")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
