"""Полный возврат оплаты снимает исходный приход из кассы и сводного отчёта."""
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from app.services.finance_service import (
    FinanceService,
    cash_effective_sql,
    clear_cash_related_caches,
)
from app.services.payment_service import PaymentService


def _memory_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE transaction_categories (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT,
            color TEXT,
            is_active INTEGER DEFAULT 1,
            is_system INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            description TEXT
        );
        INSERT INTO transaction_categories (id, name, type, color, is_active)
        VALUES (1, 'Оплата по заявке', 'income', '#22c55e', 1),
               (2, 'Возврат по заявке', 'expense', '#dc3545', 1);
        CREATE TABLE cash_transactions (
            id INTEGER PRIMARY KEY,
            category_id INTEGER,
            amount REAL,
            transaction_type TEXT,
            payment_method TEXT,
            description TEXT,
            order_id INTEGER,
            payment_id INTEGER,
            shop_sale_id INTEGER,
            transaction_date TEXT,
            created_by_id INTEGER,
            created_by_username TEXT,
            storno_of_id INTEGER,
            is_cancelled INTEGER DEFAULT 0,
            cancelled_at TEXT,
            cancelled_reason TEXT,
            cancelled_by_id INTEGER,
            cancelled_by_username TEXT
        );
        CREATE TABLE orders (id INTEGER PRIMARY KEY, order_id TEXT);
        CREATE TABLE salary_payments (
            id INTEGER PRIMARY KEY, cash_transaction_id INTEGER, user_id INTEGER, role TEXT
        );
        CREATE TABLE masters (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE managers (id INTEGER PRIMARY KEY, name TEXT);
        """
    )
    conn.commit()
    return conn


@contextmanager
def _cm(conn):
    try:
        yield conn
    finally:
        pass


def test_full_refund_void_drops_income_from_cash_summary(monkeypatch):
    conn = _memory_conn()
    today = date.today().isoformat()
    conn.execute(
        """
        INSERT INTO cash_transactions (
            category_id, amount, transaction_type, payment_method, description,
            order_id, payment_id, transaction_date, is_cancelled
        ) VALUES (1, 8500000, 'income', 'cash', 'Оплата по заявке #5581', 5581, 117, ?, 0)
        """,
        (today,),
    )
    conn.commit()
    monkeypatch.setattr("app.services.finance_service.get_db_connection", lambda: _cm(conn))

    summary_before = FinanceService.get_cash_summary(date_from=today, date_to=today)
    assert float(summary_before["total_income"]) == 8500000

    voided = FinanceService.void_cash_transactions_for_payment(
        117, reason="Возврат чека", user_id=1, username="admin", cursor=conn.cursor()
    )
    conn.commit()
    assert voided == 1
    clear_cash_related_caches()

    summary_after = FinanceService.get_cash_summary(date_from=today, date_to=today)
    assert float(summary_after["total_income"]) == 0
    assert float(summary_after["total_expense"]) == 0

    rows = FinanceService.get_transactions(date_from=today, date_to=today, limit=50)
    assert not any(abs(float(r["amount"] or 0) - 8500000) < 0.01 for r in rows)


def test_reconcile_voids_original_and_refund_expense(monkeypatch):
    conn = _memory_conn()
    today = date.today().isoformat()
    conn.executescript(
        """
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY,
            order_id INTEGER,
            amount REAL,
            payment_type TEXT,
            kind TEXT,
            refunded_of_id INTEGER,
            is_cancelled INTEGER DEFAULT 0,
            status TEXT
        );
        INSERT INTO payments (id, order_id, amount, payment_type, kind, is_cancelled)
        VALUES (10, 5581, 8500000, 'cash', 'payment', 0);
        INSERT INTO payments (id, order_id, amount, payment_type, kind, refunded_of_id, is_cancelled)
        VALUES (11, 5581, 8500000, 'cash', 'refund', 10, 0);
        """
    )
    conn.execute(
        """
        INSERT INTO cash_transactions (
            category_id, amount, transaction_type, payment_method, description,
            order_id, payment_id, transaction_date, is_cancelled
        ) VALUES
        (1, 8500000, 'income', 'cash', 'Оплата', 5581, 10, ?, 0),
        (2, 8500000, 'expense', 'cash', 'Возврат', 5581, 11, ?, 0)
        """,
        (today, today),
    )
    conn.commit()
    monkeypatch.setattr("app.services.finance_service.get_db_connection", lambda: _cm(conn))
    monkeypatch.setattr("app.services.payment_service.get_db_connection", lambda: _cm(conn))

    n = PaymentService.reconcile_full_refund_cash(original_payment_id=10, username="admin")
    assert n >= 2
    summary = FinanceService.get_cash_summary(date_from=today, date_to=today)
    assert float(summary["total_income"]) == 0
    assert float(summary["total_expense"]) == 0


def test_refund_payment_calls_void_on_full_refund():
    src = Path(PaymentService.refund_payment.__code__.co_filename).read_text(encoding="utf-8")
    chunk = src.split("def refund_payment", 1)[1].split("def delete_payment", 1)[0]
    assert "void_cash_transactions_for_payment" in chunk
    assert "full_refund" in chunk


def test_cash_effective_sql_excludes_storno_and_cancelled():
    sql = cash_effective_sql("ct")
    assert "is_cancelled" in sql
    assert "storno_of_id" in sql
    assert "sx.storno_of_id = ct.id" in sql


def test_clear_cash_related_caches_prefixes():
    # smoke: function exists and does not raise without redis
    clear_cash_related_caches()
