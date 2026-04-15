"""
Сервис для сводного отчёта по компании (Dashboard).

Рассчитывает все ключевые метрики для владельца:
- Выручка (общая, по товарам, по услугам)
- Данные по заказам (выручка, средний чек, созданные)
- Данные по магазину (выручка, средний чек)
- Актуальные данные (заказы по статусам, просроченные, по исполнителям)
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta
import re

from app.database.connection import get_db_connection
from app.utils.error_handlers import handle_service_error
from app.utils.cache import cache_result
from app.services.finance_service import FinanceService
import sqlite3
import logging

logger = logging.getLogger(__name__)
_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _has_column(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    if not (_IDENTIFIER_RE.match(table) and _IDENTIFIER_RE.match(column)):
        return False
    cur.execute(f"PRAGMA table_info({table})")
    return column in [r[1] for r in cur.fetchall()]


def _has_table(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table,),
    )
    return cur.fetchone() is not None


def _closed_status_condition(cur: sqlite3.Cursor, alias: Optional[str] = None) -> str:
    """
    Условие SQL для «заказ в закрытом статусе».
    Учитывает: английские коды (closed, completed, ...), is_final = 1, русские коды (закрыт, выдан, ...).
    """
    p = f"{alias}." if alias else ""
    parts = [f"{p}code IN ('closed', 'completed', 'done', 'finished', 'issued')"]
    if _has_column(cur, "order_statuses", "is_final"):
        parts.append(f"(COALESCE({p}is_final, 0) = 1)")
    parts.append(f"{p}code IN ('закрыт', 'выдан', 'выполнен', 'готов', 'отдан')")
    return "(" + " OR ".join(parts) + ")"


class DashboardService:
    """Сервис для сводного отчёта."""

    PERIOD_PRESETS = {
        'today': ('Сегодня', 0, 0),
        'yesterday': ('Вчера', 1, 1),
        'last_7_days': ('Последние 7 дней', 6, 0),
        'last_30_days': ('Последние 30 дней', 29, 0),
        'current_month': ('Текущий месяц', None, None),
        'quarter': ('Квартал', 89, 0),
        'half_year': ('Полгода', 182, 0),
        'last_month': ('Прошлый месяц', None, None),
        'year_to_date': ('С начала года', None, None),
    }

    @staticmethod
    def get_period_dates(preset: str = None, date_from: str = None, date_to: str = None) -> Tuple[str, str, str, str]:
        """
        Получить даты текущего и предыдущего периода.
        Returns:
            (current_from, current_to, prev_from, prev_to)
        """
        from app.utils.datetime_utils import get_moscow_now
        today = get_moscow_now().date()

        if preset == 'today':
            current_from = today
            current_to = today
        elif preset == 'yesterday':
            current_from = today - timedelta(days=1)
            current_to = today - timedelta(days=1)
        elif preset == 'last_7_days':
            current_from = today - timedelta(days=6)
            current_to = today
        elif preset == 'last_30_days':
            current_from = today - timedelta(days=29)
            current_to = today
        elif preset == 'current_month':
            current_from = today.replace(day=1)
            current_to = today
        elif preset == 'quarter':
            current_from = today - timedelta(days=89)
            current_to = today
        elif preset == 'half_year':
            current_from = today - timedelta(days=182)
            current_to = today
        elif preset == 'last_month':
            first_day_this_month = today.replace(day=1)
            last_day_prev_month = first_day_this_month - timedelta(days=1)
            current_from = last_day_prev_month.replace(day=1)
            current_to = last_day_prev_month
        elif preset == 'year_to_date':
            current_from = today.replace(month=1, day=1)
            current_to = today
        elif date_from and date_to:
            current_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            current_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        else:
            current_from = today.replace(day=1)
            current_to = today

        period_days = (current_to - current_from).days + 1
        prev_to = current_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=period_days - 1)

        return (
            current_from.isoformat(),
            current_to.isoformat(),
            prev_from.isoformat(),
            prev_to.isoformat()
        )

    @staticmethod
    def calculate_change(current: float, previous: float) -> Dict[str, Any]:
        """Рассчитать изменение: абсолютная дельта (value), % со знаком (signed_percent), направление."""
        cur = float(current)
        prev = float(previous)
        delta = round(cur - prev, 2)
        if prev == 0:
            if cur > 0:
                return {
                    'percent': 100.0,
                    'signed_percent': None,
                    'from_zero': True,
                    'direction': 'up',
                    'value': delta,
                }
            return {
                'percent': 0.0,
                'signed_percent': 0.0,
                'from_zero': False,
                'direction': 'same',
                'value': 0.0,
            }

        change_pct = ((cur - prev) / prev) * 100
        direction = 'up' if change_pct > 0 else ('down' if change_pct < 0 else 'same')
        sp = round(change_pct, 1)

        return {
            'percent': abs(sp),
            'signed_percent': sp,
            'from_zero': False,
            'direction': direction,
            'value': delta,
        }

    @staticmethod
    @cache_result(timeout=90, key_prefix='dashboard_company_summary')
    @handle_service_error
    def get_company_summary(
        date_from: str,
        date_to: str,
        prev_date_from: str,
        prev_date_to: str
    ) -> Dict[str, Any]:
        """
        Общие показатели по компании.
        Выручка = закрытые заказы (по дате закрытия в order_status_history или updated_at) + продажи магазина.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            def get_revenue_for_period(d_from: str, d_to: str) -> Dict[str, float]:
                closed_cond = _closed_status_condition(cursor, "os")
                closed_subquery = "SELECT id FROM order_statuses os_inner WHERE " + _closed_status_condition(cursor, "os_inner")
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(
                            COALESCE((SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0) +
                            COALESCE((SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0)
                        ), 0) as orders_total,
                        COALESCE(SUM(
                            COALESCE((SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0)
                        ), 0) as services_total,
                        COALESCE(SUM(
                            COALESCE((SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0)
                        ), 0) as parts_total,
                        COUNT(*) as orders_count
                    FROM orders o
                    JOIN order_statuses os ON o.status_id = os.id
                    WHERE """ + closed_cond + """
                      AND (o.hidden = 0 OR o.hidden IS NULL)
                      AND (
                        EXISTS (
                            SELECT 1 FROM order_status_history osh
                            WHERE osh.order_id = o.id
                              AND osh.new_status_id IN (""" + closed_subquery + """)
                              AND DATE(osh.created_at) >= DATE(?)
                              AND DATE(osh.created_at) <= DATE(?)
                        )
                        OR (
                            NOT EXISTS (
                                SELECT 1 FROM order_status_history osh2
                                WHERE osh2.order_id = o.id
                                  AND osh2.new_status_id IN (""" + closed_subquery + """)
                            )
                            AND DATE(o.updated_at) >= DATE(?)
                            AND DATE(o.updated_at) <= DATE(?)
                        )
                      )
                """, (d_from, d_to, d_from, d_to))
                order_row = cursor.fetchone()
                orders_revenue = float(order_row[0] or 0)
                orders_services = float(order_row[1] or 0)
                orders_parts = float(order_row[2] or 0)
                orders_count = int(order_row[3] or 0)

                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(final_amount), 0) as shop_total,
                        COUNT(*) as shop_count,
                        COALESCE(SUM(
                            (SELECT COALESCE(SUM(CASE WHEN item_type = 'service' THEN total ELSE 0 END), 0) 
                             FROM shop_sale_items WHERE shop_sale_id = ss.id)
                        ), 0) as shop_services,
                        COALESCE(SUM(
                            (SELECT COALESCE(SUM(CASE WHEN item_type = 'part' THEN total ELSE 0 END), 0) 
                             FROM shop_sale_items WHERE shop_sale_id = ss.id)
                        ), 0) as shop_parts
                    FROM shop_sales ss
                    WHERE DATE(ss.sale_date) >= DATE(?)
                      AND DATE(ss.sale_date) <= DATE(?)
                """, (d_from, d_to))
                shop_row = cursor.fetchone()
                shop_revenue = float(shop_row[0] or 0)
                shop_count = int(shop_row[1] or 0)
                shop_services = float(shop_row[2] or 0)
                shop_parts = float(shop_row[3] or 0)

                return {
                    'total': orders_revenue + shop_revenue,
                    'services': orders_services + shop_services,
                    'parts': orders_parts + shop_parts,
                    'orders_revenue': orders_revenue,
                    'orders_count': orders_count,
                    'orders_avg': orders_revenue / orders_count if orders_count > 0 else 0,
                    'shop_revenue': shop_revenue,
                    'shop_count': shop_count,
                    'shop_avg': shop_revenue / shop_count if shop_count > 0 else 0,
                }

            current = get_revenue_for_period(date_from, date_to)
            previous = get_revenue_for_period(prev_date_from, prev_date_to)

            cash_income_current = 0.0
            cash_income_previous = 0.0
            cash_expense_current = 0.0
            cash_expense_previous = 0.0
            try:
                from app.services.finance_service import FinanceService
                summary_current = FinanceService.get_cash_summary(date_from=date_from, date_to=date_to)
                summary_prev = FinanceService.get_cash_summary(date_from=prev_date_from, date_to=prev_date_to)
                cash_income_current = float(summary_current.get('total_income', 0) or 0)
                cash_income_previous = float(summary_prev.get('total_income', 0) or 0)
                cash_expense_current = float(summary_current.get('total_expense', 0) or 0)
                cash_expense_previous = float(summary_prev.get('total_expense', 0) or 0)
            except Exception as e:
                logger.warning(f"Не удалось получить данные кассы для сводки: {e}")

            return {
                'revenue': {
                    'total': current['total'],
                    'change': DashboardService.calculate_change(current['total'], previous['total'])
                },
                'services_revenue': {
                    'total': current['services'],
                    'change': DashboardService.calculate_change(current['services'], previous['services'])
                },
                'parts_revenue': {
                    'total': current['parts'],
                    'change': DashboardService.calculate_change(current['parts'], previous['parts'])
                },
                'profit': {
                    'total': cash_income_current,
                    'change': DashboardService.calculate_change(cash_income_current, cash_income_previous)
                },
                'cash_expense': {
                    'total': cash_expense_current,
                    'change': DashboardService.calculate_change(cash_expense_current, cash_expense_previous)
                },
                'orders': {
                    'revenue': current['orders_revenue'],
                    'count': current['orders_count'],
                    'avg_check': current['orders_avg'],
                    'revenue_change': DashboardService.calculate_change(current['orders_revenue'], previous['orders_revenue']),
                    'count_change': DashboardService.calculate_change(current['orders_count'], previous['orders_count']),
                    'avg_change': DashboardService.calculate_change(current['orders_avg'], previous['orders_avg']),
                },
                'shop': {
                    'revenue': current['shop_revenue'],
                    'count': current['shop_count'],
                    'avg_check': current['shop_avg'],
                    'revenue_change': DashboardService.calculate_change(current['shop_revenue'], previous['shop_revenue']),
                    'count_change': DashboardService.calculate_change(current['shop_count'], previous['shop_count']),
                    'avg_change': DashboardService.calculate_change(current['shop_avg'], previous['shop_avg']),
                },
            }

    @staticmethod
    @handle_service_error
    def get_created_orders(
        date_from: str,
        date_to: str,
        prev_date_from: str,
        prev_date_to: str
    ) -> Dict[str, Any]:
        """Данные о созданных заказах за период."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*)
                FROM orders
                WHERE DATE(created_at) >= DATE(?)
                  AND DATE(created_at) <= DATE(?)
                  AND (hidden = 0 OR hidden IS NULL)
            """, (date_from, date_to))
            current_count = cursor.fetchone()[0] or 0
            cursor.execute("""
                SELECT COUNT(*)
                FROM orders
                WHERE DATE(created_at) >= DATE(?)
                  AND DATE(created_at) <= DATE(?)
                  AND (hidden = 0 OR hidden IS NULL)
            """, (prev_date_from, prev_date_to))
            prev_count = cursor.fetchone()[0] or 0
            return {
                'count': current_count,
                'change': DashboardService.calculate_change(current_count, prev_count)
            }

    @staticmethod
    @handle_service_error
    def get_revenue_chart_data(
        date_from: str,
        date_to: str,
        prev_date_from: str,
        prev_date_to: str
    ) -> Dict[str, Any]:
        """График выручки по дням (заказы по updated_at + магазин)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            def get_daily_revenue(d_from: str, d_to: str) -> List[Dict]:
                closed_cond = _closed_status_condition(cursor, "os")
                cursor.execute("""
                    SELECT 
                        DATE(o.updated_at) as day,
                        COALESCE(SUM(
                            COALESCE((SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0) +
                            COALESCE((SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0)
                        ), 0) as revenue
                    FROM orders o
                    JOIN order_statuses os ON o.status_id = os.id
                    WHERE """ + closed_cond + """
                      AND (o.hidden = 0 OR o.hidden IS NULL)
                      AND DATE(o.updated_at) >= DATE(?)
                      AND DATE(o.updated_at) <= DATE(?)
                    GROUP BY DATE(o.updated_at)
                """, (d_from, d_to))
                orders_by_day = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
                cursor.execute("""
                    SELECT 
                        DATE(sale_date) as day,
                        COALESCE(SUM(final_amount), 0) as revenue
                    FROM shop_sales
                    WHERE DATE(sale_date) >= DATE(?)
                      AND DATE(sale_date) <= DATE(?)
                    GROUP BY DATE(sale_date)
                """, (d_from, d_to))
                shop_by_day = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
                all_days = set(orders_by_day.keys()) | set(shop_by_day.keys())
                return [
                    {
                        'date': day,
                        'orders': orders_by_day.get(day, 0),
                        'shop': shop_by_day.get(day, 0),
                        'total': orders_by_day.get(day, 0) + shop_by_day.get(day, 0)
                    }
                    for day in sorted(all_days)
                ]

            current_data = get_daily_revenue(date_from, date_to)
            prev_data = get_daily_revenue(prev_date_from, prev_date_to)
            return {
                'current': current_data,
                'previous': prev_data,
                'labels': [d['date'] for d in current_data],
                'current_values': [d['total'] for d in current_data],
                'current_orders': [d['orders'] for d in current_data],
                'current_shop': [d['shop'] for d in current_data],
            }

    @staticmethod
    @handle_service_error
    def get_orders_chart_data(
        date_from: str,
        date_to: str,
        prev_date_from: str,
        prev_date_to: str
    ) -> Dict[str, Any]:
        """График созданных заказов по дням."""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            def get_daily_orders(d_from: str, d_to: str) -> List[Dict]:
                cursor.execute("""
                    SELECT 
                        DATE(created_at) as day,
                        COUNT(*) as count
                    FROM orders
                    WHERE DATE(created_at) >= DATE(?)
                      AND DATE(created_at) <= DATE(?)
                      AND (hidden = 0 OR hidden IS NULL)
                    GROUP BY DATE(created_at)
                    ORDER BY day
                """, (d_from, d_to))
                return [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]

            current_data = get_daily_orders(date_from, date_to)
            prev_data = get_daily_orders(prev_date_from, prev_date_to)
            return {
                'current': current_data,
                'previous': prev_data,
                'labels': [d['date'] for d in current_data],
                'current_values': [d['count'] for d in current_data],
            }

    @staticmethod
    @handle_service_error
    def get_orders_by_status() -> Dict[str, Any]:
        """Текущие заказы по статусам."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            has_is_final = _has_column(cursor, "order_statuses", "is_final")
            extra_col = ", COALESCE(os.is_final, 0) as is_final" if has_is_final else ""
            cursor.execute("""
                SELECT 
                    os.id,
                    os.name,
                    os.code,
                    os.color,
                    COUNT(o.id) as count,
                    COALESCE(SUM(
                        COALESCE((SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0) +
                        COALESCE((SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0)
                    ), 0) as total_sum
                    """ + extra_col + """
                FROM order_statuses os
                LEFT JOIN orders o ON o.status_id = os.id 
                    AND (o.hidden = 0 OR o.hidden IS NULL)
                GROUP BY os.id
                ORDER BY os.sort_order, os.id
            """)
            statuses = []
            total_count = 0
            total_sum = 0
            CLOSED_CODES = ('closed', 'completed', 'done', 'finished', 'issued', 'cancelled', 'закрыт', 'выдан', 'выполнен', 'готов', 'отдан')
            for row in cursor.fetchall():
                status = {
                    'id': row[0],
                    'name': row[1],
                    'code': row[2],
                    'color': row[3] or '#6c757d',
                    'count': row[4] or 0,
                    'sum': float(row[5] or 0)
                }
                statuses.append(status)
                is_final = int(row[6] or 0) if has_is_final and len(row) > 6 else 0
                if row[2] not in CLOSED_CODES and not is_final:
                    total_count += status['count']
                    total_sum += status['sum']
            return {
                'statuses': statuses,
                'active_count': total_count,
                'active_sum': total_sum
            }

    @staticmethod
    @handle_service_error
    def get_overdue_orders() -> Dict[str, Any]:
        """Просроченные заказы (не закрытые, созданы более 7 дней назад)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            from app.utils.datetime_utils import get_moscow_now
            overdue_before = (get_moscow_now().date() - timedelta(days=7)).isoformat()
            not_closed_cond = "NOT " + _closed_status_condition(cursor, "os") + " AND (os.code IS NULL OR os.code <> 'cancelled')"
            cursor.execute("""
                SELECT 
                    o.id,
                    o.order_id,
                    o.customer_id,
                    c.name as customer_name,
                    c.phone as customer_phone,
                    o.device_id,
                    dt.name as device_type,
                    db.name as device_brand,
                    os.name as status_name,
                    os.color as status_color,
                    o.created_at,
                    COALESCE(
                        (SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0
                    ) + COALESCE(
                        (SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0
                    ) as total_sum,
                    ms.id as master_id,
                    ms.name as master_name,
                    mgr.id as manager_id,
                    mgr.name as manager_name
                FROM orders o
                JOIN order_statuses os ON o.status_id = os.id
                LEFT JOIN customers c ON o.customer_id = c.id
                LEFT JOIN devices d ON o.device_id = d.id
                LEFT JOIN device_types dt ON d.device_type_id = dt.id
                LEFT JOIN device_brands db ON d.device_brand_id = db.id
                LEFT JOIN masters ms ON o.master_id = ms.id
                LEFT JOIN managers mgr ON o.manager_id = mgr.id
                WHERE """ + not_closed_cond + """
                  AND (o.hidden = 0 OR o.hidden IS NULL)
                  AND DATE(o.created_at) < DATE(?)
                ORDER BY o.created_at ASC
                LIMIT 50
            """, (overdue_before,))
            orders = []
            total_sum = 0
            for row in cursor.fetchall():
                order = {
                    'id': row[0],
                    'order_id': row[1],
                    'customer_id': row[2],
                    'customer_name': row[3],
                    'customer_phone': row[4],
                    'device_id': row[5],
                    'device_type': row[6],
                    'device_brand': row[7],
                    'status_name': row[8],
                    'status_color': row[9] or '#6c757d',
                    'created_at': row[10],
                    'total_sum': float(row[11] or 0),
                    'master_id': row[12],
                    'master_name': row[13],
                    'manager_id': row[14],
                    'manager_name': row[15],
                }
                orders.append(order)
                total_sum += order['total_sum']
            return {
                'orders': orders,
                'count': len(orders),
                'total_sum': total_sum
            }

    @staticmethod
    @handle_service_error
    def get_accepted_orders_in_period(
        date_from: str,
        date_to: str,
        prev_date_from: str = None,
        prev_date_to: str = None,
    ) -> Dict[str, Any]:
        """Заявки, принятые в работу за период (переход в статус «принят»/«в работе» по order_status_history)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if not _has_table(cursor, "order_status_history"):
                return {'count': 0, 'orders': []}
            closed_sub = "SELECT id FROM order_statuses os_c WHERE " + _closed_status_condition(cursor, "os_c")
            accepted_cond = (
                "os.code NOT IN ('new', 'created', 'cancelled') "
                "AND osh.new_status_id NOT IN (" + closed_sub + ")"
            )
            cursor.execute(
                """
                SELECT COUNT(DISTINCT o.id) FROM order_status_history osh
                JOIN orders o ON o.id = osh.order_id
                JOIN order_statuses os ON os.id = osh.new_status_id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND DATE(osh.created_at) >= DATE(?) AND DATE(osh.created_at) <= DATE(?)
                  AND """ + accepted_cond,
                (date_from, date_to),
            )
            total_count = int((cursor.fetchone() or (0,))[0] or 0)
            prev_count = 0
            if prev_date_from and prev_date_to:
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT o.id) FROM order_status_history osh
                    JOIN orders o ON o.id = osh.order_id
                    JOIN order_statuses os ON os.id = osh.new_status_id
                    WHERE (o.hidden = 0 OR o.hidden IS NULL)
                      AND DATE(osh.created_at) >= DATE(?) AND DATE(osh.created_at) <= DATE(?)
                      AND """ + accepted_cond,
                    (prev_date_from, prev_date_to),
                )
                prev_count = int((cursor.fetchone() or (0,))[0] or 0)
            cursor.execute(
                """
                SELECT o.id, o.order_id, c.name AS customer_name, MAX(osh.created_at) AS accepted_at
                FROM order_status_history osh
                JOIN orders o ON o.id = osh.order_id
                JOIN order_statuses os ON os.id = osh.new_status_id
                LEFT JOIN customers c ON c.id = o.customer_id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND DATE(osh.created_at) >= DATE(?)
                  AND DATE(osh.created_at) <= DATE(?)
                  AND """ + accepted_cond + """
                GROUP BY o.id, o.order_id, c.name
                ORDER BY accepted_at DESC, o.id
                LIMIT 100
                """,
                (date_from, date_to),
            )
            rows = cursor.fetchall()
            orders = [
                {
                    'id': r[0],
                    'order_id': r[1],
                    'customer_name': r[2] or '—',
                    'accepted_at': r[3],
                }
                for r in rows
            ]
            out = {'count': total_count, 'orders': orders}
            if prev_date_from and prev_date_to:
                out['count_change'] = DashboardService.calculate_change(total_count, prev_count)
            return out

    @staticmethod
    @handle_service_error
    def get_closed_orders_in_period(
        date_from: str,
        date_to: str,
        prev_date_from: str = None,
        prev_date_to: str = None,
    ) -> Dict[str, Any]:
        """Заявки, закрытые за период (переход в закрытый статус по order_status_history)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if not _has_table(cursor, "order_status_history"):
                return {'count': 0, 'orders': []}
            closed_subquery = "SELECT id FROM order_statuses os_c WHERE " + _closed_status_condition(cursor, "os_c")
            cursor.execute(
                """
                SELECT COUNT(DISTINCT o.id) FROM order_status_history osh
                JOIN orders o ON o.id = osh.order_id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND osh.new_status_id IN (""" + closed_subquery + """)
                  AND DATE(osh.created_at) >= DATE(?) AND DATE(osh.created_at) <= DATE(?)
                """,
                (date_from, date_to),
            )
            total_count = int((cursor.fetchone() or (0,))[0] or 0)
            prev_count = 0
            if prev_date_from and prev_date_to:
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT o.id) FROM order_status_history osh
                    JOIN orders o ON o.id = osh.order_id
                    WHERE (o.hidden = 0 OR o.hidden IS NULL)
                      AND osh.new_status_id IN (""" + closed_subquery + """)
                      AND DATE(osh.created_at) >= DATE(?) AND DATE(osh.created_at) <= DATE(?)
                    """,
                    (prev_date_from, prev_date_to),
                )
                prev_count = int((cursor.fetchone() or (0,))[0] or 0)
            cursor.execute(
                """
                SELECT o.id, o.order_id, c.name AS customer_name, MAX(osh.created_at) AS closed_at,
                    COALESCE(
                        (SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0
                    ) + COALESCE(
                        (SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0
                    ) AS total_sum
                FROM order_status_history osh
                JOIN orders o ON o.id = osh.order_id
                LEFT JOIN customers c ON c.id = o.customer_id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND osh.new_status_id IN (""" + closed_subquery + """)
                  AND DATE(osh.created_at) >= DATE(?)
                  AND DATE(osh.created_at) <= DATE(?)
                GROUP BY o.id, o.order_id, c.name
                ORDER BY closed_at DESC, o.id
                LIMIT 100
                """,
                (date_from, date_to),
            )
            rows = cursor.fetchall()
            orders = [
                {
                    'id': r[0],
                    'order_id': r[1],
                    'customer_name': r[2] or '—',
                    'closed_at': r[3],
                    'total_sum': float(r[4] or 0),
                }
                for r in rows
            ]
            out = {'count': total_count, 'orders': orders}
            if prev_date_from and prev_date_to:
                out['count_change'] = DashboardService.calculate_change(total_count, prev_count)
            return out

    @staticmethod
    @handle_service_error
    def get_orders_by_master() -> List[Dict[str, Any]]:
        """Заказы по исполнителям (активные статусы)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            active_status_subquery = (
                "SELECT id FROM order_statuses os_a WHERE NOT "
                + _closed_status_condition(cursor, "os_a")
                + " AND (os_a.code IS NULL OR os_a.code <> 'cancelled')"
            )
            cursor.execute("""
                SELECT 
                    ms.id,
                    ms.name,
                    COUNT(o.id) as orders_count,
                    COALESCE(SUM(
                        COALESCE((SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0) +
                        COALESCE((SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0)
                    ), 0) as total_sum
                FROM masters ms
                LEFT JOIN orders o ON o.master_id = ms.id 
                    AND (o.hidden = 0 OR o.hidden IS NULL)
                    AND o.status_id IN (""" + active_status_subquery + """)
                GROUP BY ms.id
                ORDER BY orders_count DESC, ms.name
            """)
            masters = [
                {'id': row[0], 'name': row[1], 'orders_count': row[2] or 0, 'total_sum': float(row[3] or 0)}
                for row in cursor.fetchall()
            ]
            cursor.execute("""
                SELECT 
                    COUNT(o.id) as orders_count,
                    COALESCE(SUM(
                        COALESCE((SELECT SUM(price * quantity) FROM order_services WHERE order_id = o.id), 0) +
                        COALESCE((SELECT SUM(price * quantity) FROM order_parts WHERE order_id = o.id), 0)
                    ), 0) as total_sum
                FROM orders o
                WHERE o.master_id IS NULL
                  AND (o.hidden = 0 OR o.hidden IS NULL)
                  AND o.status_id IN (""" + active_status_subquery + """)
            """)
            row = cursor.fetchone()
            if row and row[0] > 0:
                masters.append({
                    'id': None,
                    'name': 'Без мастера',
                    'orders_count': row[0],
                    'total_sum': float(row[1] or 0)
                })
            return masters

    @staticmethod
    @handle_service_error
    def get_cashflow_summary(
        date_from: str,
        date_to: str,
        prev_date_from: str,
        prev_date_to: str,
    ) -> Dict[str, Any]:
        """Cashflow из cash_transactions за период."""
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cur = conn.cursor()
            has_cancelled = _has_column(cur, "cash_transactions", "is_cancelled")
            not_cancelled = " AND (ct.is_cancelled = 0 OR ct.is_cancelled IS NULL)" if has_cancelled else ""

            def fetch(d_from: str, d_to: str) -> Dict[str, Any]:
                cur.execute(
                    f"""
                    SELECT
                        COALESCE(SUM(CASE WHEN ct.transaction_type = 'income' THEN ct.amount ELSE 0 END), 0) AS income_total,
                        COALESCE(SUM(CASE WHEN ct.transaction_type = 'expense' THEN ct.amount ELSE 0 END), 0) AS expense_total
                    FROM cash_transactions ct
                    WHERE DATE(ct.transaction_date) >= DATE(?)
                      AND DATE(ct.transaction_date) <= DATE(?)
                      {not_cancelled}
                    """,
                    (d_from, d_to),
                )
                row = cur.fetchone() or {}
                income_total = float(row["income_total"] or 0)
                expense_total = float(row["expense_total"] or 0)
                cur.execute(
                    f"""
                    SELECT
                        ct.payment_method AS payment_method,
                        ct.transaction_type AS transaction_type,
                        COUNT(*) AS cnt,
                        COALESCE(SUM(ct.amount), 0) AS amount
                    FROM cash_transactions ct
                    WHERE DATE(ct.transaction_date) >= DATE(?)
                      AND DATE(ct.transaction_date) <= DATE(?)
                      {not_cancelled}
                    GROUP BY ct.payment_method, ct.transaction_type
                    ORDER BY amount DESC
                    """,
                    (d_from, d_to),
                )
                by_method = [dict(r) for r in cur.fetchall()]
                return {
                    "income_total": income_total,
                    "expense_total": expense_total,
                    "net_total": income_total - expense_total,
                    "by_method": by_method,
                }

            current = fetch(date_from, date_to)
            previous = fetch(prev_date_from, prev_date_to)
            return {
                "income": {
                    "total": current["income_total"],
                    "change": DashboardService.calculate_change(current["income_total"], previous["income_total"]),
                },
                "expense": {
                    "total": current["expense_total"],
                    "change": DashboardService.calculate_change(current["expense_total"], previous["expense_total"]),
                },
                "net": {
                    "total": current["net_total"],
                    "change": DashboardService.calculate_change(current["net_total"], previous["net_total"]),
                },
                "by_method": current["by_method"],
            }

    @staticmethod
    @handle_service_error
    def get_receivables_summary() -> Dict[str, Any]:
        """Дебиторка по активным заявкам."""
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(payments)")
            pay_cols = [r[1] for r in cur.fetchall()]
            has_kind = "kind" in pay_cols
            has_status = "status" in pay_cols
            has_cancelled = "is_cancelled" in pay_cols
            paid_expr = "SUM(CASE WHEN p.kind = 'refund' THEN -p.amount ELSE p.amount END)" if has_kind else "SUM(p.amount)"
            paid_where = ["1=1"]
            if has_cancelled:
                paid_where.append("(p.is_cancelled = 0 OR p.is_cancelled IS NULL)")
            if has_status:
                paid_where.append("p.status = 'captured'")
            if has_kind:
                paid_where.append("p.kind IN ('payment', 'deposit', 'refund')")
            paid_where_sql = " AND ".join(paid_where)
            payments_agg_sql = f"""
                SELECT
                    p.order_id,
                    COALESCE({paid_expr}, 0) AS paid
                FROM payments p
                WHERE {paid_where_sql}
                GROUP BY p.order_id
            """
            closed_ids_subquery = (
                "SELECT id FROM order_statuses os_r WHERE "
                + _closed_status_condition(cur, "os_r")
                + " OR os_r.code = 'cancelled'"
            )
            cur.execute(
                f"""
                SELECT
                    o.id,
                    o.order_id,
                    o.created_at,
                    o.customer_id,
                    c.name AS customer_name,
                    c.phone AS customer_phone,
                    os.name AS status_name,
                    os.color AS status_color,
                    COALESCE(osum.services_total, 0) AS services_total,
                    COALESCE(psum.parts_total, 0) AS parts_total,
                    COALESCE(pay.paid, 0) AS paid,
                    (COALESCE(osum.services_total, 0) + COALESCE(psum.parts_total, 0)) AS total_sum,
                    ((COALESCE(osum.services_total, 0) + COALESCE(psum.parts_total, 0)) - COALESCE(pay.paid, 0)) AS debt
                FROM orders o
                LEFT JOIN customers c ON c.id = o.customer_id
                LEFT JOIN order_statuses os ON os.id = o.status_id
                LEFT JOIN (
                    SELECT order_id, SUM(price * quantity) AS services_total
                    FROM order_services
                    GROUP BY order_id
                ) osum ON osum.order_id = o.id
                LEFT JOIN (
                    SELECT order_id, SUM(price * quantity) AS parts_total
                    FROM order_parts
                    GROUP BY order_id
                ) psum ON psum.order_id = o.id
                LEFT JOIN (
                    {payments_agg_sql}
                ) pay ON pay.order_id = o.id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND o.status_id NOT IN ({closed_ids_subquery})
                  AND ((COALESCE(osum.services_total, 0) + COALESCE(psum.parts_total, 0)) - COALESCE(pay.paid, 0)) > 0
                ORDER BY debt DESC, o.created_at ASC
                LIMIT 50
                """
            )
            items = [dict(r) for r in cur.fetchall()]
            total_debt = sum(float(i.get("debt") or 0) for i in items)
            today = date.today()
            aging = {
                "c_0_7": 0,
                "c_8_30": 0,
                "c_31_60": 0,
                "c_60_plus": 0,
                "s_0_7": 0.0,
                "s_8_30": 0.0,
                "s_31_60": 0.0,
                "s_60_plus": 0.0,
            }
            for item in items:
                created_raw = item.get("created_at")
                created_date = None
                if isinstance(created_raw, datetime):
                    created_date = created_raw.date()
                elif isinstance(created_raw, date):
                    created_date = created_raw
                elif created_raw:
                    created_txt = str(created_raw).strip()
                    try:
                        created_date = datetime.fromisoformat(created_txt.replace(" ", "T")).date()
                    except ValueError:
                        try:
                            created_date = datetime.strptime(created_txt[:10], "%Y-%m-%d").date()
                        except ValueError:
                            created_date = None
                if not created_date:
                    continue
                debt = float(item.get("debt") or 0)
                age_days = max(0, (today - created_date).days)
                if age_days <= 7:
                    aging["c_0_7"] += 1
                    aging["s_0_7"] += debt
                elif age_days <= 30:
                    aging["c_8_30"] += 1
                    aging["s_8_30"] += debt
                elif age_days <= 60:
                    aging["c_31_60"] += 1
                    aging["s_31_60"] += debt
                else:
                    aging["c_60_plus"] += 1
                    aging["s_60_plus"] += debt
            return {
                "total_debt": total_debt,
                "orders_with_debt": len(items),
                "aging": aging,
                "items": items,
            }

    @staticmethod
    @handle_service_error
    def get_customers_kpis(date_from: str, date_to: str) -> Dict[str, Any]:
        """KPI клиентов: новые, активные, возвращающиеся за период."""
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                WITH first_orders AS (
                    SELECT customer_id, MIN(DATE(created_at)) AS first_date
                    FROM orders
                    WHERE (hidden = 0 OR hidden IS NULL)
                    GROUP BY customer_id
                )
                SELECT
                    (SELECT COUNT(*) FROM customers c WHERE DATE(c.created_at) >= DATE(?) AND DATE(c.created_at) <= DATE(?)) AS new_customers,
                    (SELECT COUNT(DISTINCT o.customer_id) FROM orders o
                        WHERE (o.hidden = 0 OR o.hidden IS NULL)
                          AND DATE(o.created_at) >= DATE(?) AND DATE(o.created_at) <= DATE(?)
                    ) AS active_customers,
                    (SELECT COUNT(DISTINCT o.customer_id) FROM orders o
                        JOIN first_orders fo ON fo.customer_id = o.customer_id
                        WHERE (o.hidden = 0 OR o.hidden IS NULL)
                          AND DATE(o.created_at) >= DATE(?) AND DATE(o.created_at) <= DATE(?)
                          AND DATE(fo.first_date) < DATE(?)
                    ) AS returning_customers
                """,
                (date_from, date_to, date_from, date_to, date_from, date_to, date_from),
            )
            row = dict(cur.fetchone() or {})
            cur.execute(
                """
                SELECT
                    c.id,
                    c.name,
                    c.phone,
                    COUNT(DISTINCT o.id) AS orders_count,
                    COALESCE(SUM(COALESCE(osum.services_total, 0) + COALESCE(psum.parts_total, 0)), 0) AS total_sum
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                LEFT JOIN (
                    SELECT order_id, SUM(price * quantity) AS services_total
                    FROM order_services
                    GROUP BY order_id
                ) osum ON osum.order_id = o.id
                LEFT JOIN (
                    SELECT order_id, SUM(price * quantity) AS parts_total
                    FROM order_parts
                    GROUP BY order_id
                ) psum ON psum.order_id = o.id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND DATE(o.created_at) >= DATE(?)
                  AND DATE(o.created_at) <= DATE(?)
                GROUP BY c.id
                ORDER BY total_sum DESC
                LIMIT 10
                """,
                (date_from, date_to),
            )
            top_customers = [dict(r) for r in cur.fetchall()]
            return {
                "new_customers": int(row.get("new_customers") or 0),
                "active_customers": int(row.get("active_customers") or 0),
                "returning_customers": int(row.get("returning_customers") or 0),
                "top_customers": top_customers,
            }

    @staticmethod
    @handle_service_error
    def get_warehouse_kpis(date_from: str, date_to: str) -> Dict[str, Any]:
        """KPI склада и закупок за период."""
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cur = conn.cursor()
            if not _has_table(cur, "parts"):
                return {
                    "parts_count": 0,
                    "retail_value": 0.0,
                    "cost_value": 0.0,
                    "low_stock_count": 0,
                    "purchases_count": 0,
                    "purchases_total": 0.0,
                }
            has_parts_deleted = _has_column(cur, "parts", "is_deleted")
            parts_where = "WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL)" if has_parts_deleted else ""
            price_col = "retail_price" if _has_column(cur, "parts", "retail_price") else "price"
            purchase_col = "purchase_price" if _has_column(cur, "parts", "purchase_price") else "0"
            cur.execute(
                f"""
                SELECT
                    COUNT(*) AS parts_count,
                    COALESCE(SUM(COALESCE(p.{price_col}, 0) * COALESCE(p.stock_quantity, 0)), 0) AS retail_value,
                    COALESCE(SUM(COALESCE(p.{purchase_col}, 0) * COALESCE(p.stock_quantity, 0)), 0) AS cost_value,
                    COALESCE(SUM(CASE WHEN COALESCE(p.stock_quantity, 0) <= COALESCE(p.min_quantity, 0) AND COALESCE(p.min_quantity, 0) > 0 THEN 1 ELSE 0 END), 0) AS low_stock_count
                FROM parts p
                {parts_where}
                """
            )
            parts_row = dict(cur.fetchone() or {})
            p_row = {"purchases_count": 0, "purchases_total": 0}
            if _has_table(cur, "purchases"):
                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS purchases_count,
                        COALESCE(SUM(total_amount), 0) AS purchases_total
                    FROM purchases
                    WHERE status = 'completed'
                      AND DATE(purchase_date) >= DATE(?)
                      AND DATE(purchase_date) <= DATE(?)
                    """,
                    (date_from, date_to),
                )
                p_row = dict(cur.fetchone() or {})
            return {
                "parts_count": int(parts_row.get("parts_count") or 0),
                "retail_value": float(parts_row.get("retail_value") or 0),
                "cost_value": float(parts_row.get("cost_value") or 0),
                "low_stock_count": int(parts_row.get("low_stock_count") or 0),
                "purchases_count": int(p_row.get("purchases_count") or 0),
                "purchases_total": float(p_row.get("purchases_total") or 0),
            }

    @staticmethod
    @handle_service_error
    def get_salary_period_summary(
        date_from: str,
        date_to: str,
        prev_date_from: str,
        prev_date_to: str,
    ) -> Dict[str, Any]:
        """Начисления и выплаты зарплаты за период."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            accrued_current = accrued_prev = paid_current = paid_prev = 0
            if _has_table(cur, "salary_accruals"):
                cur.execute(
                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_accruals WHERE DATE(created_at) >= DATE(?) AND DATE(created_at) <= DATE(?)",
                    (date_from, date_to),
                )
                accrued_current = int(cur.fetchone()[0] or 0)
                cur.execute(
                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_accruals WHERE DATE(created_at) >= DATE(?) AND DATE(created_at) <= DATE(?)",
                    (prev_date_from, prev_date_to),
                )
                accrued_prev = int(cur.fetchone()[0] or 0)
            if _has_table(cur, "salary_payments"):
                cur.execute(
                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_payments WHERE DATE(payment_date) >= DATE(?) AND DATE(payment_date) <= DATE(?)",
                    (date_from, date_to),
                )
                paid_current = int(cur.fetchone()[0] or 0)
                cur.execute(
                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_payments WHERE DATE(payment_date) >= DATE(?) AND DATE(payment_date) <= DATE(?)",
                    (prev_date_from, prev_date_to),
                )
                paid_prev = int(cur.fetchone()[0] or 0)
            return {
                "accrued_cents": accrued_current,
                "accrued_change": DashboardService.calculate_change(accrued_current / 100.0, accrued_prev / 100.0),
                "paid_cents": paid_current,
                "paid_change": DashboardService.calculate_change(paid_current / 100.0, paid_prev / 100.0),
            }

    @staticmethod
    @cache_result(timeout=60, key_prefix='dashboard_full')
    @handle_service_error
    def get_full_dashboard(
        preset: str = None,
        date_from: str = None,
        date_to: str = None
    ) -> Dict[str, Any]:
        """Все данные для сводного отчёта."""
        current_from, current_to, prev_from, prev_to = DashboardService.get_period_dates(
            preset, date_from, date_to
        )
        summary = DashboardService.get_company_summary(current_from, current_to, prev_from, prev_to)
        created_orders = DashboardService.get_created_orders(current_from, current_to, prev_from, prev_to)
        accepted_orders = DashboardService.get_accepted_orders_in_period(
            current_from, current_to, prev_from, prev_to
        )
        closed_orders = DashboardService.get_closed_orders_in_period(
            current_from, current_to, prev_from, prev_to
        )
        revenue_chart = DashboardService.get_revenue_chart_data(current_from, current_to, prev_from, prev_to)
        orders_chart = DashboardService.get_orders_chart_data(current_from, current_to, prev_from, prev_to)
        orders_by_status = DashboardService.get_orders_by_status()
        overdue_orders = DashboardService.get_overdue_orders()
        orders_by_master = DashboardService.get_orders_by_master()
        cashflow = DashboardService.get_cashflow_summary(current_from, current_to, prev_from, prev_to)
        receivables = DashboardService.get_receivables_summary()
        customers = DashboardService.get_customers_kpis(current_from, current_to)
        warehouse = DashboardService.get_warehouse_kpis(current_from, current_to)
        salary = DashboardService.get_salary_period_summary(current_from, current_to, prev_from, prev_to)
        profit_report = None
        product_analytics = None
        try:
            profit_report = FinanceService.get_profit_report(date_from=current_from, date_to=current_to)
        except Exception:
            pass
        try:
            product_analytics = FinanceService.get_product_analytics(date_from=current_from, date_to=current_to)
        except Exception:
            pass
        return {
            'period': {
                'current_from': current_from,
                'current_to': current_to,
                'prev_from': prev_from,
                'prev_to': prev_to,
                'preset': preset,
            },
            'summary': summary,
            'created_orders': created_orders,
            'accepted_orders': accepted_orders,
            'closed_orders': closed_orders,
            'revenue_chart': revenue_chart,
            'orders_chart': orders_chart,
            'orders_by_status': orders_by_status,
            'overdue_orders': overdue_orders,
            'orders_by_master': orders_by_master,
            'cashflow': cashflow,
            'receivables': receivables,
            'customers': customers,
            'warehouse': warehouse,
            'salary': salary,
            'profit_report': profit_report,
            'product_analytics': product_analytics,
        }
