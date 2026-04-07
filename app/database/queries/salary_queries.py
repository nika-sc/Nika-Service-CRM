"""
SQL запросы для работы с зарплатой.
"""
from typing import Any, Dict, List, Optional
from app.database.connection import get_db_connection
from app.utils.datetime_utils import get_moscow_now_str
import sqlite3
import logging

logger = logging.getLogger(__name__)


class SalaryQueries:
    """Класс для SQL-запросов по зарплате."""
    
    @staticmethod
    def create_accrual(
        user_id: int,
        role: str,
        amount_cents: int,
        base_amount_cents: int,
        profit_cents: int,
        rule_type: str,
        rule_value: float,
        calculated_from: str,
        calculated_from_id: Optional[int] = None,
        service_id: Optional[int] = None,
        part_id: Optional[int] = None,
        vat_included: int = 0,
        created_at: Optional[str] = None,
        order_id: Optional[int] = None,
        shop_sale_id: Optional[int] = None,
    ) -> int:
        """
        Создает запись о начислении зарплаты.
        Ровно один из order_id или shop_sale_id должен быть задан.

        Args:
            created_at: Дата/время начисления (YYYY-MM-DD HH:MM:SS). Если None — текущее время (Москва).
            order_id: ID заявки (для начислений по заявке).
            shop_sale_id: ID продажи магазина (для начислений по магазину).

        Returns:
            ID созданной записи
        """
        if (order_id is None and shop_sale_id is None) or (order_id is not None and shop_sale_id is not None):
            raise ValueError("Укажите ровно один из order_id или shop_sale_id")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if created_at is None or not str(created_at).strip():
                    created_at = get_moscow_now_str()
                else:
                    created_at = str(created_at).strip()
                cursor.execute('''
                    INSERT INTO salary_accruals (
                        order_id, shop_sale_id, user_id, role,
                        amount_cents, base_amount_cents, profit_cents,
                        rule_type, rule_value,
                        calculated_from, calculated_from_id,
                        service_id, part_id,
                        vat_included, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_id, shop_sale_id, user_id, role,
                    amount_cents, base_amount_cents, profit_cents,
                    rule_type, rule_value,
                    calculated_from, calculated_from_id,
                    service_id, part_id,
                    vat_included, created_at
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании начисления зарплаты: {e}", exc_info=True)
            raise
    
    @staticmethod
    def delete_accruals_for_order(order_id: int) -> int:
        """
        Удаляет все начисления зарплаты по заявке.

        Returns:
            Количество удаленных записей
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM salary_accruals WHERE order_id = ?', (order_id,))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Ошибка при удалении начислений для заявки {order_id}: {e}", exc_info=True)
            raise

    @staticmethod
    def delete_accruals_for_shop_sale(shop_sale_id: int) -> int:
        """
        Удаляет все начисления зарплаты по продаже магазина (например при возврате).

        Returns:
            Количество удаленных записей
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM salary_accruals WHERE shop_sale_id = ?', (shop_sale_id,))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Ошибка при удалении начислений для продажи магазина {shop_sale_id}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_accruals_for_order(order_id: int) -> List[Dict]:
        """
        Получает все начисления зарплаты по заявке.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список начислений
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        sa.*,
                        m.name as master_name,
                        mg.name as manager_name
                    FROM salary_accruals sa
                    LEFT JOIN masters m ON m.id = sa.user_id AND sa.role = 'master'
                    LEFT JOIN managers mg ON mg.id = sa.user_id AND sa.role = 'manager'
                    WHERE sa.order_id = ?
                    ORDER BY sa.created_at DESC
                ''', (order_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении начислений для заявки {order_id}: {e}", exc_info=True)
            return []

    @staticmethod
    def get_accruals_for_order_with_details(order_id: int) -> List[Dict]:
        """
        Получает все начисления по заявке с полной детализацией (order_uuid, source_service_name, source_part_name).
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        sa.*,
                        o.order_id as order_uuid,
                        m.name as master_name,
                        mg.name as manager_name,
                        svc.name as source_service_name,
                        pt.name as source_part_name
                    FROM salary_accruals sa
                    LEFT JOIN orders o ON o.id = sa.order_id
                    LEFT JOIN masters m ON m.id = sa.user_id AND sa.role = 'master'
                    LEFT JOIN managers mg ON mg.id = sa.user_id AND sa.role = 'manager'
                    LEFT JOIN services svc ON svc.id = COALESCE(sa.service_id, CASE WHEN sa.calculated_from = 'service' THEN sa.calculated_from_id END)
                    LEFT JOIN parts pt ON pt.id = COALESCE(sa.part_id, CASE WHEN sa.calculated_from = 'part' THEN sa.calculated_from_id END)
                    WHERE sa.order_id = ?
                    ORDER BY sa.created_at DESC
                ''', (order_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении начислений для заявки {order_id}: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_salary_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        user_id: Optional[int] = None,
        role: Optional[str] = None
    ) -> List[Dict]:
        """
        Получает отчет по зарплате.
        
        Args:
            date_from: Дата начала
            date_to: Дата окончания
            user_id: Фильтр по сотруднику
            role: Фильтр по роли ('master' или 'manager')
            
        Returns:
            Список начислений
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                where_clauses = []
                params = []
                
                if date_from:
                    where_clauses.append('DATE(sa.created_at) >= DATE(?)')
                    params.append(date_from)
                if date_to:
                    where_clauses.append('DATE(sa.created_at) <= DATE(?)')
                    params.append(date_to)
                if user_id:
                    where_clauses.append('sa.user_id = ?')
                    params.append(user_id)
                if role:
                    where_clauses.append('sa.role = ?')
                    params.append(role)
                
                where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
                
                cursor.execute(f'''
                    SELECT 
                        sa.*,
                        o.order_id as order_uuid,
                        o.created_at as order_created_at,
                        m.name as master_name,
                        mg.name as manager_name,
                        os.name as status_name,
                        svc.name as source_service_name,
                        pt.name as source_part_name,
                        rule_m.name as rule_master_name,
                        rule_mgr.name as rule_manager_name
                    FROM salary_accruals sa
                    LEFT JOIN orders o ON o.id = sa.order_id
                    LEFT JOIN order_statuses os ON os.id = o.status_id
                    LEFT JOIN masters m ON m.id = sa.user_id AND sa.role = 'master'
                    LEFT JOIN managers mg ON mg.id = sa.user_id AND sa.role = 'manager'
                    LEFT JOIN services svc ON svc.id = COALESCE(sa.service_id, CASE WHEN sa.calculated_from = 'service' THEN sa.calculated_from_id END)
                    LEFT JOIN parts pt ON pt.id = COALESCE(sa.part_id, CASE WHEN sa.calculated_from = 'part' THEN sa.calculated_from_id END)
                    LEFT JOIN masters rule_m ON rule_m.id = sa.calculated_from_id AND sa.calculated_from = 'master'
                    LEFT JOIN managers rule_mgr ON rule_mgr.id = sa.calculated_from_id AND sa.calculated_from = 'manager'
                    {where_sql}
                    ORDER BY sa.created_at DESC
                ''', params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении отчета по зарплате: {e}", exc_info=True)
            return []

    @staticmethod
    def get_salary_report_by_period_date(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        user_id: Optional[int] = None,
        role: Optional[str] = None
    ) -> List[Dict]:
        """
        Отчёт по зарплате: начисления за период по дате оплаты (заявки) и дате продажи (магазин).
        Совпадает с логикой кассы: приход за период = платежи с payment_date в периоде + продажи с sale_date в периоде.
        """
        if not date_from and not date_to:
            return SalaryQueries.get_salary_report(date_from=date_from, date_to=date_to, user_id=user_id, role=role)
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                pay_cols = [r[1] for r in cursor.execute("PRAGMA table_info(payments)").fetchall()]
                kind_filter = " AND (p.kind IS NULL OR p.kind != 'refund')" if 'kind' in pay_cols else ""
                status_filter = " AND p.status = 'captured'" if 'status' in pay_cols else " AND (p.status IS NULL OR p.status != 'cancelled')"
                d_from = date_from or '1900-01-01'
                d_to = date_to or '2099-12-31'
                orders_in_period_sql = f"""
                    SELECT DISTINCT p.order_id FROM payments p
                    WHERE (p.is_cancelled = 0 OR p.is_cancelled IS NULL) {status_filter} {kind_filter}
                      AND DATE(COALESCE(p.payment_date, p.created_at)) >= DATE(?)
                      AND DATE(COALESCE(p.payment_date, p.created_at)) <= DATE(?)
                """
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shop_sales'")
                has_shop = cursor.fetchone() is not None
                cursor.execute("PRAGMA table_info(salary_accruals)")
                sa_cols = [r[1] for r in cursor.fetchall()]
                has_shop_sale_id = 'shop_sale_id' in sa_cols
                period_condition = "sa.order_id IN (" + orders_in_period_sql + ")"
                params: List[Any] = [d_from, d_to]
                if has_shop and has_shop_sale_id:
                    period_condition += """
                      OR sa.shop_sale_id IN (
                          SELECT id FROM shop_sales
                          WHERE DATE(sale_date) >= DATE(?) AND DATE(sale_date) <= DATE(?)
                      )
                    """
                    params.extend([d_from, d_to])
                where_clauses = ["(" + period_condition + ")"]
                if user_id:
                    where_clauses.append("sa.user_id = ?")
                    params.append(user_id)
                if role:
                    where_clauses.append("sa.role = ?")
                    params.append(role)
                where_sql = "WHERE " + " AND ".join(where_clauses)
                cursor.execute(f'''
                    SELECT
                        sa.*,
                        o.order_id as order_uuid,
                        o.created_at as order_created_at,
                        m.name as master_name,
                        mg.name as manager_name,
                        os.name as status_name,
                        svc.name as source_service_name,
                        pt.name as source_part_name,
                        rule_m.name as rule_master_name,
                        rule_mgr.name as rule_manager_name
                    FROM salary_accruals sa
                    LEFT JOIN orders o ON o.id = sa.order_id
                    LEFT JOIN order_statuses os ON os.id = o.status_id
                    LEFT JOIN masters m ON m.id = sa.user_id AND sa.role = 'master'
                    LEFT JOIN managers mg ON mg.id = sa.user_id AND sa.role = 'manager'
                    LEFT JOIN services svc ON svc.id = COALESCE(sa.service_id, CASE WHEN sa.calculated_from = 'service' THEN sa.calculated_from_id END)
                    LEFT JOIN parts pt ON pt.id = COALESCE(sa.part_id, CASE WHEN sa.calculated_from = 'part' THEN sa.calculated_from_id END)
                    LEFT JOIN masters rule_m ON rule_m.id = sa.calculated_from_id AND sa.calculated_from = 'master'
                    LEFT JOIN managers rule_mgr ON rule_mgr.id = sa.calculated_from_id AND sa.calculated_from = 'manager'
                    {where_sql}
                    ORDER BY sa.created_at DESC
                ''', params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка get_salary_report_by_period_date: {e}", exc_info=True)
            return []

    @staticmethod
    def get_orders_revenue_in_period(
        order_ids: List[int],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[int, int]:
        """Выручка по заявкам только по платежам с датой в периоде (для сверки с кассой)."""
        if not order_ids or (not date_from and not date_to):
            return {oid: 0 for oid in order_ids}
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' * len(order_ids))
                pay_cols = [r[1] for r in cursor.execute("PRAGMA table_info(payments)").fetchall()]
                kind_filter = " AND (kind IS NULL OR kind != 'refund')" if 'kind' in pay_cols else ""
                status_filter = " AND status = 'captured'" if 'status' in pay_cols else " AND (status IS NULL OR status != 'cancelled')"
                has_kind = 'kind' in pay_cols
                d_from = date_from or '1900-01-01'
                d_to = date_to or '2099-12-31'
                sum_expr = "COALESCE(SUM(CASE WHEN kind = 'refund' THEN -amount ELSE amount END), 0) * 100" if has_kind else "COALESCE(SUM(amount), 0) * 100"
                cursor.execute(f'''
                    SELECT order_id, {sum_expr} as revenue_cents
                    FROM payments
                    WHERE order_id IN ({placeholders})
                      AND (is_cancelled = 0 OR is_cancelled IS NULL)
                      {status_filter}
                      {kind_filter}
                      AND DATE(COALESCE(payment_date, created_at)) >= DATE(?)
                      AND DATE(COALESCE(payment_date, created_at)) <= DATE(?)
                    GROUP BY order_id
                ''', list(order_ids) + [d_from, d_to])
                result = {oid: 0 for oid in order_ids}
                for row in cursor.fetchall():
                    result[row[0]] = int(row[1] or 0)
                return result
        except Exception as e:
            logger.error(f"Ошибка get_orders_revenue_in_period: {e}", exc_info=True)
            return {oid: 0 for oid in order_ids}

    @staticmethod
    def get_salary_summary(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        user_id: Optional[int] = None,
        role: Optional[str] = None
    ) -> Dict:
        """
        Получает сводку по зарплате (итоги).
        
        Returns:
            Словарь с итогами
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                where_clauses = []
                params = []
                
                if date_from:
                    where_clauses.append('DATE(sa.created_at) >= DATE(?)')
                    params.append(date_from)
                if date_to:
                    where_clauses.append('DATE(sa.created_at) <= DATE(?)')
                    params.append(date_to)
                if user_id:
                    where_clauses.append('sa.user_id = ?')
                    params.append(user_id)
                if role:
                    where_clauses.append('sa.role = ?')
                    params.append(role)
                
                where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
                
                cursor.execute(f'''
                    SELECT 
                        COUNT(*) as total_accruals,
                        SUM(sa.amount_cents) as total_amount_cents,
                        SUM(sa.profit_cents) as total_profit_cents,
                        COUNT(DISTINCT sa.user_id) as unique_users,
                        COUNT(DISTINCT sa.order_id) as unique_orders
                    FROM salary_accruals sa
                    {where_sql}
                ''', params)
                row = cursor.fetchone()
                return {
                    'total_accruals': row[0] or 0,
                    'total_amount_cents': row[1] or 0,
                    'total_profit_cents': row[2] or 0,
                    'unique_users': row[3] or 0,
                    'unique_orders': row[4] or 0
                }
        except Exception as e:
            logger.error(f"Ошибка при получении сводки по зарплате: {e}", exc_info=True)
            return {
                'total_accruals': 0,
                'total_amount_cents': 0,
                'total_profit_cents': 0,
                'unique_users': 0,
                'unique_orders': 0
            }

    @staticmethod
    def get_orders_revenue_and_costs(order_ids: List[int]) -> Dict[int, Dict]:
        """
        По заявкам возвращает: выручка (платежи), расход на товары, расход на услуги,
        сумма начисленной зарплаты по заявке, итого руководителю (выручка - расходы - зарплата).

        Returns:
            { order_id: { revenue_cents, parts_cost_cents, services_cost_cents,
                          salary_order_cents, owner_net_cents } }
        """
        if not order_ids:
            return {}
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' * len(order_ids))

                cursor.execute("PRAGMA table_info(payments)")
                pay_cols = [row[1] for row in cursor.fetchall()]
                has_kind = 'kind' in pay_cols
                has_status = 'status' in pay_cols

                if has_kind:
                    if has_status:
                        cursor.execute(f'''
                            SELECT order_id,
                                   COALESCE(SUM(CASE WHEN kind = 'refund' THEN -amount ELSE amount END), 0) * 100 as revenue_cents
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                            GROUP BY order_id
                        ''', order_ids)
                    else:
                        cursor.execute(f'''
                            SELECT order_id,
                                   COALESCE(SUM(CASE WHEN kind = 'refund' THEN -amount ELSE amount END), 0) * 100 as revenue_cents
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            GROUP BY order_id
                        ''', order_ids)
                else:
                    cursor.execute(f'''
                        SELECT order_id, COALESCE(SUM(amount), 0) * 100 as revenue_cents
                        FROM payments
                        WHERE order_id IN ({placeholders})
                          AND (is_cancelled = 0 OR is_cancelled IS NULL)
                        GROUP BY order_id
                    ''', order_ids)
                revenue_rows = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}

                cursor.execute(f'''
                    SELECT order_id, COALESCE(SUM(COALESCE(purchase_price, 0) * quantity), 0) * 100 as cents
                    FROM order_parts
                    WHERE order_id IN ({placeholders})
                    GROUP BY order_id
                ''', order_ids)
                parts_rows = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}

                cursor.execute(f'''
                    SELECT order_id, COALESCE(SUM(COALESCE(cost_price, 0) * quantity), 0) * 100 as cents
                    FROM order_services
                    WHERE order_id IN ({placeholders})
                    GROUP BY order_id
                ''', order_ids)
                services_rows = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}

                cursor.execute(f'''
                    SELECT order_id, COALESCE(SUM(amount_cents), 0) as salary_cents
                    FROM salary_accruals
                    WHERE order_id IN ({placeholders})
                    GROUP BY order_id
                ''', order_ids)
                salary_rows = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}

                result = {}
                for oid in order_ids:
                    revenue_cents = revenue_rows.get(oid, 0)
                    parts_cents = parts_rows.get(oid, 0)
                    services_cents = services_rows.get(oid, 0)
                    salary_cents = salary_rows.get(oid, 0)
                    # Прибыль заявки = выручка − себестоимость (одна на заявку, не по ролям)
                    order_profit_cents = revenue_cents - parts_cents - services_cents
                    owner_net_cents = order_profit_cents - salary_cents
                    result[oid] = {
                        'revenue_cents': revenue_cents,
                        'parts_cost_cents': parts_cents,
                        'services_cost_cents': services_cents,
                        'salary_order_cents': salary_cents,
                        'order_profit_cents': order_profit_cents,
                        'owner_net_cents': owner_net_cents,
                    }
                return result
        except Exception as e:
            logger.error(f"Ошибка при получении выручки/расходов по заявкам: {e}", exc_info=True)
            return {oid: {'revenue_cents': 0, 'parts_cost_cents': 0, 'services_cost_cents': 0,
                         'salary_order_cents': 0, 'order_profit_cents': 0, 'owner_net_cents': 0} for oid in order_ids}

    @staticmethod
    def get_shop_sales_revenue(shop_sale_ids: List[int]) -> Dict[int, int]:
        """
        По списку ID продаж магазина возвращает выручку в копейках (total_amount из shop_sales).
        Returns: { shop_sale_id: revenue_cents }
        """
        if not shop_sale_ids:
            return {}
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shop_sales'")
                if not cursor.fetchone():
                    return {}
                placeholders = ','.join('?' * len(shop_sale_ids))
                cursor.execute(
                    f"SELECT id, COALESCE(total_amount, 0) FROM shop_sales WHERE id IN ({placeholders})",
                    shop_sale_ids,
                )
                return {row[0]: int(round(float(row[1] or 0) * 100)) for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Ошибка при получении выручки по продажам магазина: {e}", exc_info=True)
            return {}

    @staticmethod
    def get_order_items_with_profit(order_ids: List[int]) -> Dict[int, Dict[str, List[Dict]]]:
        """
        По заявкам возвращает услуги и товары с прибылью по каждой позиции.
        Returns: { order_id: { 'services': [{name, profit_cents}], 'parts': [{name, profit_cents}] } }
        """
        if not order_ids:
            return {}
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' * len(order_ids))

                cursor.execute(f'''
                    SELECT os.order_id, COALESCE(os.name, s.name) as name,
                           (COALESCE(os.price, 0) * COALESCE(os.quantity, 1) -
                            COALESCE(os.cost_price, 0) * COALESCE(os.quantity, 1)) * 100 as profit_cents
                    FROM order_services os
                    LEFT JOIN services s ON s.id = os.service_id
                    WHERE os.order_id IN ({placeholders})
                    ORDER BY os.order_id, os.id
                ''', order_ids)
                services_by_order: Dict[int, List[Dict]] = {}
                for row in cursor.fetchall():
                    oid, name, profit_cents = row[0], row[1], int(row[2] or 0)
                    if name:
                        services_by_order.setdefault(oid, []).append({
                            'name': name,
                            'profit_cents': max(0, profit_cents),
                        })

                cursor.execute(f'''
                    SELECT op.order_id, COALESCE(op.name, p.name) as name,
                           (COALESCE(op.price, 0) * COALESCE(op.quantity, 1) -
                            COALESCE(op.purchase_price, 0) * COALESCE(op.quantity, 1)) * 100 as profit_cents
                    FROM order_parts op
                    LEFT JOIN parts p ON p.id = op.part_id
                    WHERE op.order_id IN ({placeholders})
                    ORDER BY op.order_id, op.id
                ''', order_ids)
                parts_by_order: Dict[int, List[Dict]] = {}
                for row in cursor.fetchall():
                    oid, name, profit_cents = row[0], row[1], int(row[2] or 0)
                    if name:
                        parts_by_order.setdefault(oid, []).append({
                            'name': name,
                            'profit_cents': max(0, profit_cents),
                        })

                return {
                    oid: {
                        'services': services_by_order.get(oid, []),
                        'parts': parts_by_order.get(oid, []),
                    }
                    for oid in order_ids
                }
        except Exception as e:
            logger.error(f"Ошибка при получении услуг/товаров по заявкам: {e}", exc_info=True)
            return {oid: {'services': [], 'parts': []} for oid in order_ids}


