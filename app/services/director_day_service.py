"""
Сводка дня для директора: принято / закрыто / касса / зарплата.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from app.database.connection import get_db_connection
from app.services.finance_service import FinanceService
from app.utils.datetime_utils import get_moscow_now
from app.utils.error_handlers import handle_service_error
import logging

logger = logging.getLogger(__name__)


def _parse_day(day: Optional[str]) -> str:
    """YYYY-MM-DD, по умолчанию сегодня (МСК)."""
    if day:
        try:
            return datetime.strptime(day[:10], "%Y-%m-%d").date().isoformat()
        except ValueError:
            pass
    return get_moscow_now().date().isoformat()


class DirectorDayService:
    """Компактные метрики за один календарный день."""

    @staticmethod
    @handle_service_error
    def get_day_snapshot(day: Optional[str] = None) -> Dict[str, Any]:
        day_iso = _parse_day(day)
        day_date = datetime.strptime(day_iso, "%Y-%m-%d").date()
        prev_iso = (day_date - timedelta(days=1)).isoformat()

        current = DirectorDayService._metrics_for_day(day_iso)
        previous = DirectorDayService._metrics_for_day(prev_iso)

        def _delta(cur: float, prev: float) -> Dict[str, Any]:
            d = round(float(cur) - float(prev), 2)
            if prev == 0:
                direction = "up" if cur > 0 else ("same" if cur == 0 else "down")
            else:
                direction = "up" if d > 0 else ("down" if d < 0 else "same")
            return {"value": d, "direction": direction}

        return {
            "day": day_iso,
            "prev_day": prev_iso,
            "is_today": day_iso == get_moscow_now().date().isoformat(),
            "orders": {
                "accepted": current["accepted"],
                "closed": current["closed"],
                "accepted_delta": _delta(current["accepted"], previous["accepted"]),
                "closed_delta": _delta(current["closed"], previous["closed"]),
                "accepted_prepayment": current["accepted_prepayment"],
                "closed_revenue": current["closed_revenue"],
            },
            "cash": current["cash"],
            "cash_prev": previous["cash"],
            "cash_delta": {
                "income": _delta(current["cash"]["income"], previous["cash"]["income"]),
                "expense": _delta(current["cash"]["expense"], previous["cash"]["expense"]),
                "net": _delta(current["cash"]["net"], previous["cash"]["net"]),
            },
            "salary": current["salary"],
            "salary_prev": previous["salary"],
            "salary_delta": {
                "accrued": _delta(current["salary"]["accrued"], previous["salary"]["accrued"]),
                "paid": _delta(current["salary"]["paid"], previous["salary"]["paid"]),
            },
            "links": {
                "orders_accepted": f"/all_orders?date_from={day_iso}&date_to={day_iso}",
                "finance_cash": f"/finance/cash?date_from={day_iso}&date_to={day_iso}",
                "salary": "/salary",
            },
        }

    @staticmethod
    def _metrics_for_day(day_iso: str) -> Dict[str, Any]:
        accepted = 0
        accepted_prepayment = 0.0
        closed = 0
        closed_revenue = 0.0

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT COUNT(*),
                       COALESCE(SUM(COALESCE(NULLIF(prepayment::text, '')::numeric, 0)), 0)
                FROM orders
                WHERE COALESCE(is_deleted, 0) = 0
                  AND DATE(created_at) = DATE(?)
                """,
                (day_iso,),
            )
            row = cursor.fetchone()
            accepted = int(row[0] or 0)
            accepted_prepayment = float(row[1] or 0)

            # Закрытия за день: переход в статус с accrues_salary или is_final
            try:
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT osh.order_id)
                    FROM order_status_history osh
                    JOIN order_statuses ns ON ns.id = osh.new_status_id
                    JOIN orders o ON o.id = osh.order_id
                    WHERE DATE(osh.created_at) = DATE(?)
                      AND COALESCE(o.is_deleted, 0) = 0
                      AND (
                            COALESCE(ns.accrues_salary, 0) = 1
                         OR COALESCE(ns.is_final, 0) = 1
                         OR LOWER(COALESCE(ns.code, '')) IN ('closed', 'completed', 'done', 'finished', 'issued')
                      )
                    """,
                    (day_iso,),
                )
                closed = int((cursor.fetchone() or [0])[0] or 0)

                cursor.execute(
                    """
                    SELECT COALESCE(SUM(
                        COALESCE((SELECT SUM(price * quantity) FROM order_services s WHERE s.order_id = x.order_id), 0)
                      + COALESCE((SELECT SUM(price * quantity) FROM order_parts p WHERE p.order_id = x.order_id), 0)
                    ), 0)
                    FROM (
                        SELECT DISTINCT osh.order_id AS order_id
                        FROM order_status_history osh
                        JOIN order_statuses ns ON ns.id = osh.new_status_id
                        JOIN orders o ON o.id = osh.order_id
                        WHERE DATE(osh.created_at) = DATE(?)
                          AND COALESCE(o.is_deleted, 0) = 0
                          AND (
                                COALESCE(ns.accrues_salary, 0) = 1
                             OR COALESCE(ns.is_final, 0) = 1
                             OR LOWER(COALESCE(ns.code, '')) IN ('closed', 'completed', 'done', 'finished', 'issued')
                          )
                    ) x
                    """,
                    (day_iso,),
                )
                closed_revenue = float((cursor.fetchone() or [0])[0] or 0)
            except Exception as e:
                logger.debug("director day closed via history failed (%s), fallback", e)
                cursor.execute(
                    """
                    SELECT COUNT(*),
                           COALESCE(SUM(
                             COALESCE((SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0)
                           + COALESCE((SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0)
                           ), 0)
                    FROM orders o
                    JOIN order_statuses ns ON ns.id = o.status_id
                    WHERE COALESCE(o.is_deleted, 0) = 0
                      AND DATE(COALESCE(o.updated_at, o.created_at)) = DATE(?)
                      AND (
                            COALESCE(ns.accrues_salary, 0) = 1
                         OR COALESCE(ns.is_final, 0) = 1
                         OR LOWER(COALESCE(ns.code, '')) IN ('closed', 'completed', 'done', 'finished', 'issued')
                      )
                    """,
                    (day_iso,),
                )
                row = cursor.fetchone()
                closed = int(row[0] or 0)
                closed_revenue = float(row[1] or 0)

            # Начислено / выплачено за день (руб.)
            accrued = 0.0
            paid = 0.0
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount_cents), 0) / 100.0
                    FROM salary_accruals
                    WHERE DATE(created_at) = DATE(?)
                    """,
                    (day_iso,),
                )
                accrued = float((cursor.fetchone() or [0])[0] or 0)
            except Exception:
                accrued = 0.0
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount_cents), 0) / 100.0
                    FROM salary_payments
                    WHERE DATE(payment_date) = DATE(?)
                    """,
                    (day_iso,),
                )
                paid = float((cursor.fetchone() or [0])[0] or 0)
            except Exception:
                paid = 0.0

            # Текущий долг по ЗП (снимок «сейчас»)
            owed = 0.0
            try:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(owed), 0) / 100.0 FROM (
                      SELECT
                        COALESCE((SELECT SUM(amount_cents) FROM salary_accruals sa WHERE sa.user_id = u.user_id AND sa.role = u.role), 0)
                      + COALESCE((SELECT SUM(amount_cents) FROM salary_bonuses sb WHERE sb.user_id = u.user_id AND sb.role = u.role), 0)
                      - COALESCE((SELECT SUM(amount_cents) FROM salary_fines sf WHERE sf.user_id = u.user_id AND sf.role = u.role), 0)
                      - COALESCE((SELECT SUM(amount_cents) FROM salary_payments sp WHERE sp.user_id = u.user_id AND sp.role = u.role), 0)
                        AS owed
                      FROM (
                        SELECT DISTINCT user_id, role FROM salary_accruals
                        UNION
                        SELECT DISTINCT user_id, role FROM salary_payments
                        UNION
                        SELECT DISTINCT user_id, role FROM salary_bonuses
                        UNION
                        SELECT DISTINCT user_id, role FROM salary_fines
                      ) u
                    ) t
                    WHERE owed > 0
                    """
                )
                owed = float((cursor.fetchone() or [0])[0] or 0)
            except Exception as e:
                logger.warning("director day salary owed failed: %s", e)
                owed = 0.0

        cash_summary = FinanceService.get_cash_summary(date_from=day_iso, date_to=day_iso) or {}
        income = float(cash_summary.get("total_income") or 0)
        expense = float(cash_summary.get("total_expense") or 0)
        opening = float(cash_summary.get("opening_balance") or 0)
        closing = float(cash_summary.get("balance") if cash_summary.get("balance") is not None else (opening + income - expense))
        by_method = cash_summary.get("balance_by_method") or cash_summary.get("by_payment_method") or {}

        return {
            "accepted": accepted,
            "accepted_prepayment": round(accepted_prepayment, 2),
            "closed": closed,
            "closed_revenue": round(closed_revenue, 2),
            "cash": {
                "opening": round(opening, 2),
                "income": round(income, 2),
                "expense": round(expense, 2),
                "net": round(income - expense, 2),
                "closing": round(closing, 2),
                "by_method": by_method,
            },
            "salary": {
                "accrued": round(accrued, 2),
                "paid": round(paid, 2),
                "owed": round(owed, 2),
            },
        }
