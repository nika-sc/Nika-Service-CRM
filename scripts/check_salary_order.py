#!/usr/bin/env python3
"""
Диагностика зарплаты по заявке: salary_accruals, платежи, услуги, товары, правила.
Использование: python scripts/check_salary_order.py [order_id или order_uuid]
Пример: python scripts/check_salary_order.py 9812
        python scripts/check_salary_order.py a2277479-3d9a-42aa-8046-0f2ae8287d05
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db_connection
import sqlite3


def find_order(cursor, arg):
    """Находит заявку по id или UUID."""
    if str(arg).isdigit():
        cursor.execute("SELECT id, order_id, master_id, manager_id, status_id FROM orders WHERE id = ?", (int(arg),))
    else:
        cursor.execute("SELECT id, order_id, master_id, manager_id, status_id FROM orders WHERE order_id = ?", (str(arg),))
    return cursor.fetchone()


def main():
    # Заявка #9812 или UUID a2277479-3d9a-42aa-8046-0f2ae8287d05
    order_arg = sys.argv[1] if len(sys.argv) > 1 else "9812"

    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cursor = conn.cursor()

        # 1. Найти заявку
        row = find_order(cursor, order_arg)
        if not row:
            print(f"Заявка не найдена: {order_arg}")
            return
        oid, uuid, master_id, manager_id, status_id = row[0], row[1], row[2], row[3], row[4]
        print("=" * 80)
        print(f"ЗАЯВКА #{oid} (UUID: {uuid})")
        print(f"  master_id={master_id}, manager_id={manager_id}, status_id={status_id}")
        print("=" * 80)

        # 2. Платежи (payment_type, не payment_method)
        cursor.execute("PRAGMA table_info(payments)")
        pay_cols_info = [r[1] for r in cursor.fetchall()]
        has_kind = 'kind' in pay_cols_info
        sel = "id, amount, payment_type, created_at" + (", kind" if has_kind else "")
        cursor.execute(f"""
            SELECT {sel}
            FROM payments
            WHERE order_id = ? AND (is_cancelled = 0 OR is_cancelled IS NULL)
            ORDER BY created_at
        """, (oid,))
        payments = cursor.fetchall()
        pay_cols = [d[0] for d in cursor.description]
        total_paid = 0
        print("\n--- ПЛАТЕЖИ ---")
        for p in payments:
            d = dict(zip(pay_cols, p))
            amt = float(d.get('amount') or 0)
            if d.get('kind') == 'refund':
                amt = -amt
            total_paid += amt
            print(f"  id={d.get('id')} amount={d.get('amount')} type={d.get('payment_type')} "
                  f"created={d.get('created_at')} kind={d.get('kind','payment')}")
        print(f"  ИТОГО оплачено: {total_paid:.2f} руб.")

        # 3. Услуги
        cursor.execute("""
            SELECT os.id, os.service_id, os.name, os.quantity, os.price, os.cost_price, os.executor_id
            FROM order_services os
            WHERE os.order_id = ?
        """, (oid,))
        services = cursor.fetchall()
        svc_cols = [d[0] for d in cursor.description]
        print("\n--- УСЛУГИ ---")
        for s in services:
            d = dict(zip(svc_cols, s))
            qty = float(d.get('quantity') or 1)
            price = float(d.get('price') or 0)
            cost = float(d.get('cost_price') or 0)
            rev = price * qty
            prof = rev - cost * qty
            print(f"  id={d.get('id')} name={d.get('name')} qty={qty} price={price} cost={cost} "
                  f"| выручка={rev:.2f} прибыль={prof:.2f} executor_id={d.get('executor_id')}")

        # 4. Товары
        cursor.execute("""
            SELECT op.id, op.part_id, op.name, op.quantity, op.price, op.purchase_price, op.executor_id
            FROM order_parts op
            WHERE op.order_id = ?
        """, (oid,))
        parts = cursor.fetchall()
        pt_cols = [d[0] for d in cursor.description]
        print("\n--- ТОВАРЫ ---")
        for p in parts:
            d = dict(zip(pt_cols, p))
            qty = float(d.get('quantity') or 1)
            price = float(d.get('price') or 0)
            cost = float(d.get('purchase_price') or 0)
            rev = price * qty
            prof = rev - cost * qty
            print(f"  id={d.get('id')} name={d.get('name')} qty={qty} price={price} cost={cost} "
                  f"| выручка={rev:.2f} прибыль={prof:.2f} executor_id={d.get('executor_id')}")

        # 5. Итоги по заявке
        cursor.execute("""
            SELECT
                (SELECT COALESCE(SUM(price * quantity), 0) FROM order_services WHERE order_id = ?) +
                (SELECT COALESCE(SUM(price * quantity), 0) FROM order_parts WHERE order_id = ?) as revenue
        """, (oid, oid))
        revenue = float(cursor.fetchone()[0] or 0)
        cursor.execute("""
            SELECT
                (SELECT COALESCE(SUM(cost_price * quantity), 0) FROM order_services WHERE order_id = ?) +
                (SELECT COALESCE(SUM(purchase_price * quantity), 0) FROM order_parts WHERE order_id = ?) as cost
        """, (oid, oid))
        cost = float(cursor.fetchone()[0] or 0)
        profit = revenue - cost
        print(f"\n--- ИТОГО ПО ЗАЯВКЕ ---")
        print(f"  Выручка (услуги+товары): {revenue:.2f} руб.")
        print(f"  Себестоимость: {cost:.2f} руб.")
        print(f"  Прибыль: {profit:.2f} руб.")

        # 6. Правила мастера 34 и менеджера 18
        print("\n--- ПРАВИЛА МАСТЕРА 34 ---")
        cursor.execute("""
            SELECT salary_rule_type, salary_rule_value,
                   salary_percent_services, salary_percent_parts, salary_percent_shop_parts, name
            FROM masters WHERE id = 34
        """, ())
        m = cursor.fetchone()
        if m:
            print(f"  name={m[5]} rule_type={m[0]} rule_value={m[1]} "
                  f"percent_services={m[2]} percent_parts={m[3]} percent_shop={m[4]}")
        else:
            print("  Мастер 34 не найден")

        print("\n--- ПРАВИЛА МЕНЕДЖЕРА 18 ---")
        cursor.execute("""
            SELECT salary_rule_type, salary_rule_value,
                   salary_percent_services, salary_percent_parts, salary_percent_shop_parts, name
            FROM managers WHERE id = 18
        """, ())
        mg = cursor.fetchone()
        if mg:
            print(f"  name={mg[5]} rule_type={mg[0]} rule_value={mg[1]} "
                  f"percent_services={mg[2]} percent_parts={mg[3]} percent_shop={mg[4]}")
        else:
            print("  Менеджер 18 не найден")

        # 7. Начисления salary_accruals
        cursor.execute("""
            SELECT sa.*, o.id as ord_num
            FROM salary_accruals sa
            LEFT JOIN orders o ON o.id = sa.order_id
            WHERE sa.order_id = ?
            ORDER BY sa.created_at
        """, (oid,))
        accruals = cursor.fetchall()
        acc_cols = [d[0] for d in cursor.description]
        print("\n--- НАЧИСЛЕНИЯ (salary_accruals) ---")
        for a in accruals:
            d = dict(zip(acc_cols, a))
            amt = (d.get('amount_cents') or 0) / 100
            base = (d.get('base_amount_cents') or 0) / 100
            prof_c = (d.get('profit_cents') or 0) / 100
            rule_val = float(d.get('rule_value') or 0)
            calc = d.get('calculated_from')
            calc_id = d.get('calculated_from_id')
            print(f"  id={d.get('id')} user_id={d.get('user_id')} role={d.get('role')} "
                  f"amount={amt:.2f} руб. base={base:.2f} profit={prof_c:.2f} "
                  f"rule={d.get('rule_type')} {rule_val}% from={calc}({calc_id}) "
                  f"created={d.get('created_at')}")
            # Проверка: 10% от profit -> amount
            if d.get('rule_type') == 'percent' and rule_val and prof_c > 0:
                expected = prof_c * rule_val / 100
                print(f"    -> ожидаемо {rule_val}% от прибыли {prof_c:.2f} = {expected:.2f} руб., в таблице {amt:.2f} руб.")

        # 8. Начисления мастера 34 и менеджера 18 за 28.02.2026
        print("\n" + "=" * 80)
        print("НАЧИСЛЕНИЯ ЗА 28.02.2026")
        print("=" * 80)
        for emp_id, role, label in [(34, 'master', 'Мастер 34'), (18, 'manager', 'Менеджер 18')]:
            cursor.execute("""
                SELECT sa.id, sa.order_id, sa.amount_cents, sa.base_amount_cents, sa.profit_cents,
                       sa.rule_type, sa.rule_value, sa.calculated_from, sa.created_at, o.id as ord_num
                FROM salary_accruals sa
                LEFT JOIN orders o ON o.id = sa.order_id
                WHERE sa.user_id = ? AND sa.role = ?
                  AND DATE(sa.created_at) = '2026-02-28'
                ORDER BY sa.created_at
            """, (emp_id, role))
            rows = cursor.fetchall()
            print(f"\n--- {label} ---")
            for r in rows:
                amt = (r[2] or 0) / 100
                base = (r[3] or 0) / 100
                prof = (r[4] or 0) / 100
                print(f"  Заявка #{r[9]} amount={amt:.2f} руб. base={base:.2f} profit={prof:.2f} "
                      f"rule={r[5]} {r[6]}% from={r[7]} created={r[8]}")

        # 9. Разбивка начислений по оплатам (как в кабинете /salary/employee/34/master)
        print("\n" + "=" * 80)
        print("РАЗБИВКА НАЧИСЛЕНИЙ ПО ОПЛАТАМ (как в кабинете зарплаты)")
        print("=" * 80)
        cursor.execute("""
            SELECT sa.id, sa.user_id, sa.role, sa.amount_cents, sa.rule_type, sa.rule_value
            FROM salary_accruals sa WHERE sa.order_id = ?
        """, (oid,))
        accs = cursor.fetchall()
        cursor.execute("""
            SELECT id, amount, created_at, payment_type
            FROM payments
            WHERE order_id = ? AND (is_cancelled = 0 OR is_cancelled IS NULL)
              AND (kind IS NULL OR kind != 'refund')
            ORDER BY created_at
        """, (oid,))
        pays = cursor.fetchall()
        total_pay = sum(float(p[1] or 0) for p in pays)
        if total_pay > 0 and accs:
            for sa in accs:
                uid, role, amt_c = sa[1], sa[2], sa[3]
                amt_total = amt_c / 100
                print(f"\n  user_id={uid} role={role}: всего начислено {amt_total:.2f} руб. (rule {sa[4]} {sa[5]}%)")
                for p in pays:
                    pay_amt = float(p[1] or 0)
                    share = amt_total * (pay_amt / total_pay)
                    print(f"    оплата {p[0]} {pay_amt:.0f} руб. ({p[3]}) {p[2]} -> доля начисления: {share:.2f} руб.")

        print("\nГотово.")


if __name__ == '__main__':
    main()
