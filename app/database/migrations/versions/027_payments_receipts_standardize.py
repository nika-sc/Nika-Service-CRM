"""
Миграция 027: Стандартизация оплат и добавление чеков (receipts).

Цели:
- Единый источник истины по оплатам: таблица payments (включая предоплату как kind='deposit')
- Статусы платежей (status) и идемпотентность (idempotency_key)
- Таблица чеков (payment_receipts) для фискализации/печати/интеграции
- Перенос legacy предоплаты orders.prepayment_cents -> payments(kind='deposit') и привязка к cash_transactions
"""

import logging
import sqlite3
from datetime import datetime

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def _has_column(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return column in [r[1] for r in cur.fetchall()]


def _get_or_create_category_id(cur: sqlite3.Cursor, name: str, cat_type: str = "income") -> int:
    cur.execute(
        "SELECT id FROM transaction_categories WHERE name = ? AND type = ? LIMIT 1",
        (name, cat_type),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        """
        INSERT INTO transaction_categories (name, type, description, color, is_system, is_active, sort_order)
        VALUES (?, ?, ?, ?, 1, 1, 999)
        """,
        (name, cat_type, f"Системная категория: {name}", "#6c757d"),
    )
    return int(cur.lastrowid)


def up():
    logger.info("Применение миграции 027_payments_receipts_standardize")
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cur = conn.cursor()

        # 1) Расширяем payments (если колонок ещё нет)
        payments_new_cols = [
            ("kind", "TEXT NOT NULL DEFAULT 'payment'"),  # payment|deposit|refund|adjustment
            ("status", "TEXT NOT NULL DEFAULT 'captured'"),  # pending|captured|cancelled|refunded
            ("idempotency_key", "TEXT"),
            ("external_provider", "TEXT"),
            ("external_payment_id", "TEXT"),
            ("captured_at", "TEXT"),
            ("refunded_of_id", "INTEGER REFERENCES payments(id)"),
        ]
        for col, ddl in payments_new_cols:
            if not _has_column(cur, "payments", col):
                try:
                    cur.execute(f"ALTER TABLE payments ADD COLUMN {col} {ddl}")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Не удалось добавить колонку payments.{col}: {e}")

        # 2) Идемпотентность: уникальный ключ, если idempotency_key задан
        try:
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_payments_idempotency_key
                ON payments(idempotency_key)
                WHERE idempotency_key IS NOT NULL AND TRIM(idempotency_key) != ''
                """
            )
        except sqlite3.OperationalError as e:
            logger.warning(f"Не удалось создать индекс ux_payments_idempotency_key: {e}")

        # 3) Таблица чеков
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id INTEGER NOT NULL,
                receipt_type TEXT NOT NULL CHECK(receipt_type IN ('sell', 'refund')),
                status TEXT NOT NULL DEFAULT 'manual' CHECK(status IN ('queued', 'sent', 'done', 'failed', 'manual')),
                provider TEXT,
                provider_receipt_id TEXT,
                payload TEXT,
                response TEXT,
                error TEXT,
                created_by_id INTEGER,
                created_by_username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                printed_at TIMESTAMP,
                FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by_id) REFERENCES users(id)
            )
            """
        )
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_receipts_payment_id ON payment_receipts(payment_id)")
        except sqlite3.OperationalError:
            pass

        # 4) Добавляем/гарантируем системные категории
        try:
            _get_or_create_category_id(cur, "Оплата по заявке", "income")
        except Exception as e:
            logger.warning(f"Не удалось создать категорию 'Оплата по заявке': {e}")
        try:
            _get_or_create_category_id(cur, "Возврат по заявке", "expense")
        except Exception as e:
            logger.warning(f"Не удалось создать категорию 'Возврат по заявке': {e}")

        # 5) Перенос legacy предоплаты в payments(kind='deposit')
        #    Логика:
        #    - если в orders есть prepayment_cents > 0, создаём payments запись kind='deposit'
        #    - пытаемся привязать существующую cash_transaction категории 'Предоплата' (если была создана ранее)
        #    - затем обнуляем orders.prepayment_cents и orders.prepayment (legacy) чтобы не было двойного учёта
        if _has_column(cur, "orders", "prepayment_cents"):
            try:
                cur.execute(
                    """
                    SELECT id, prepayment_cents
                    FROM orders
                    WHERE prepayment_cents IS NOT NULL AND prepayment_cents > 0
                    """
                )
                rows = cur.fetchall()
                if rows:
                    prepay_cat_id = None
                    try:
                        prepay_cat_id = _get_or_create_category_id(cur, "Предоплата", "income")
                    except Exception:
                        prepay_cat_id = None

                    for r in rows:
                        order_id = int(r["id"])
                        cents = int(r["prepayment_cents"] or 0)
                        amount = float(cents) / 100.0

                        # Если уже есть deposit платеж — пропускаем
                        if _has_column(cur, "payments", "kind"):
                            cur.execute(
                                """
                                SELECT id FROM payments
                                WHERE order_id = ? AND kind = 'deposit' AND (is_cancelled = 0 OR is_cancelled IS NULL)
                                LIMIT 1
                                """,
                                (order_id,),
                            )
                            if cur.fetchone():
                                continue

                        # Создаём payment
                        now = datetime.utcnow().isoformat()
                        cur.execute(
                            """
                            INSERT INTO payments (
                                order_id, amount, payment_type, comment,
                                created_by, created_by_username,
                                payment_date, created_at,
                                kind, status, captured_at
                            )
                            VALUES (?, ?, 'cash', ?, NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'deposit', 'captured', ?)
                            """,
                            (order_id, amount, "Миграция: предоплата (orders.prepayment_cents)", now),
                        )
                        payment_id = int(cur.lastrowid)

                        # Привязка/создание кассовой операции
                        if prepay_cat_id is not None:
                            # 1) попытка найти существующую кассовую операцию предоплаты без payment_id
                            try:
                                cur.execute(
                                    """
                                    SELECT id FROM cash_transactions
                                    WHERE order_id = ?
                                      AND category_id = ?
                                      AND transaction_type = 'income'
                                      AND (payment_id IS NULL)
                                      AND (is_cancelled = 0 OR is_cancelled IS NULL)
                                      AND ABS(amount - ?) < 0.0001
                                    ORDER BY created_at DESC
                                    LIMIT 1
                                    """,
                                    (order_id, prepay_cat_id, amount),
                                )
                                tx = cur.fetchone()
                                if tx:
                                    cur.execute(
                                        "UPDATE cash_transactions SET payment_id = ? WHERE id = ?",
                                        (payment_id, int(tx[0])),
                                    )
                                else:
                                    # 2) если не нашли — создаём новую (как fallback)
                                    cur.execute(
                                        """
                                        INSERT INTO cash_transactions (
                                            category_id, amount, transaction_type, payment_method, description,
                                            order_id, payment_id, transaction_date,
                                            created_by_id, created_by_username
                                        )
                                        VALUES (?, ?, 'income', 'cash', ?, ?, ?, DATE('now'), NULL, NULL)
                                        """,
                                        (prepay_cat_id, amount, "Предоплата (миграция)", order_id, payment_id),
                                    )
                            except Exception as e:
                                logger.warning(f"Не удалось привязать/создать cash_transaction для предоплаты заказа {order_id}: {e}")

                    # Обнуляем legacy поле, чтобы не было двойного учёта
                    cur.execute("UPDATE orders SET prepayment_cents = 0 WHERE prepayment_cents IS NOT NULL AND prepayment_cents > 0")
                    if _has_column(cur, "orders", "prepayment"):
                        cur.execute("UPDATE orders SET prepayment = '' WHERE prepayment IS NOT NULL AND TRIM(prepayment) != ''")
            except Exception as e:
                logger.warning(f"Не удалось перенести legacy предоплату: {e}")

        conn.commit()
        logger.info("Миграция 027_payments_receipts_standardize применена")


def down():
    logger.warning("Откат миграции 027_payments_receipts_standardize не поддерживается (SQLite DROP COLUMN ограничен)")


