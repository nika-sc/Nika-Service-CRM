"""
Сервис для работы с дашбордом зарплаты и аналитикой сотрудников.
"""
from typing import Dict, List, Optional, Any, Tuple
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.error_handlers import handle_service_error
from app.utils.datetime_utils import get_moscow_now_str, get_moscow_now
from app.services.salary_service import SalaryService
from datetime import datetime, timedelta
import sqlite3
import logging

logger = logging.getLogger(__name__)


def _normalize_date_iso(date_str: Optional[str]) -> Optional[str]:
    """Приводит дату к безопасному формату YYYY-MM-DD или возвращает None."""
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip()
    base = s[:10]
    try:
        if len(base) == 10 and base[4] == "-" and base[7] == "-":
            return datetime.strptime(base, "%Y-%m-%d").strftime("%Y-%m-%d")
        if "." in base:
            parsed = datetime.strptime(base, "%d.%m.%Y")
            return parsed.strftime("%Y-%m-%d")
        return None
    except ValueError:
        return None


def _is_master_role(role: Optional[str]) -> bool:
    """Роль считается «мастер»: master или master_* (кастомная)."""
    if not role:
        return False
    r = role.strip().lower()
    return r == 'master' or r.startswith('master_')


def _is_manager_role(role: Optional[str]) -> bool:
    """Роль считается «менеджер»: manager или manager_* (кастомная)."""
    if not role:
        return False
    r = role.strip().lower()
    return r == 'manager' or r.startswith('manager_')


class SalaryDashboardService:
    """Сервис для работы с дашбордом зарплаты."""

    @staticmethod
    def _get_overall_owed_with_cursor(cursor, user_id: int, role: str) -> int:
        """Считает общий долг (начислено + премии - штрафы - выплаты) без фильтра по периоду."""
        def _sum(table, date_col=None):
            cursor.execute(
                f"""
                SELECT COALESCE(SUM(amount_cents), 0)
                FROM {table}
                WHERE user_id = ? AND role = ?
                """,
                (user_id, role),
            )
            return int(cursor.fetchone()[0] or 0)

        accrued = _sum('salary_accruals')
        bonuses = _sum('salary_bonuses')
        fines = _sum('salary_fines')
        paid = _sum('salary_payments')
        return accrued + bonuses - fines - paid
    
    @staticmethod
    def get_employee_id_by_user(user_id: int, user_role: str) -> Optional[Tuple[int, str]]:
        """
        Получает ID сотрудника (master_id или manager_id) по user_id.
        
        Args:
            user_id: ID пользователя из таблицы users
            user_role: Роль пользователя ('master', 'master_*', 'manager', 'manager_*')
            
        Returns:
            Tuple[employee_id, role] или None если не найден
        """
        if not user_id or user_id <= 0:
            return None
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                r = (user_role or '').strip().lower()
                
                if r == 'master' or r.startswith('master_'):
                    cursor.execute('SELECT id FROM masters WHERE user_id = ? AND (active = 1 OR active IS NULL)', (user_id,))
                    row = cursor.fetchone()
                    if row:
                        return (row[0], 'master')
                elif r == 'manager' or r.startswith('manager_'):
                    cursor.execute('SELECT id FROM managers WHERE user_id = ? AND (active = 1 OR active IS NULL)', (user_id,))
                    row = cursor.fetchone()
                    if row:
                        return (row[0], 'manager')
        except Exception as e:
            logger.error(f"Ошибка при получении employee_id для user_id {user_id}: {e}", exc_info=True)
        
        return None
    
    @staticmethod
    @handle_service_error
    def get_salary_period_totals(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Считает итоговую выручку и прибыль за период по заявкам (без дублирования).
        Одна заявка учитывается один раз: выручка = сумма платежей по заявке, прибыль = прибыль заявки.

        Returns:
            - total_revenue_cents: сумма платежей по всем заявкам с начислениями в периоде
            - total_profit_cents: сумма прибыли по этим заявкам
            - total_orders_count: количество уникальных заявок
        """
        # Важно: для сверки с /finance/cash "Выручка в /salary" должна учитывать
        # не только начисления по заявкам (order_id), но и продажи магазина (shop_sale_id).
        try:
            report = SalaryService.get_salary_report(date_from=date_from, date_to=date_to, user_id=None, role=None)
            summary = (report or {}).get("summary") or {}
            accruals = (report or {}).get("accruals") or []

            # Одна "заявка" здесь = unique order_id (shop_sale_id не считается заявкой).
            order_ids = {a.get("order_id") for a in accruals if a.get("order_id")}

            return {
                "total_revenue_cents": int(summary.get("total_revenue_cents") or 0),
                "total_profit_cents": int(summary.get("total_profit_cents") or 0),
                "total_orders_count": len(order_ids),
            }
        except Exception as e:
            logger.error(f"Ошибка при расчете итогов зарплаты: {e}", exc_info=True)
            return {"total_revenue_cents": 0, "total_profit_cents": 0, "total_orders_count": 0}

    @staticmethod
    @handle_service_error
    def get_employees_with_stats(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        role: Optional[str] = None,  # 'master', 'manager', None (все)
        status: Optional[str] = 'active',  # 'active', 'inactive', None (все)
        sort_by: str = 'profit',  # 'profit', 'revenue', 'orders', 'salary'
        current_user_id: Optional[int] = None,
        current_user_role: Optional[str] = None
    ) -> List[Dict]:
        """
        Возвращает список сотрудников с агрегированной статистикой с учетом прав доступа.

        Args:
            date_from: Дата начала периода (YYYY-MM-DD)
            date_to: Дата окончания периода (YYYY-MM-DD)
            role: Фильтр по роли ('master', 'manager')
            status: Фильтр по статусу ('active', 'inactive')
            sort_by: Сортировка ('profit', 'revenue', 'orders', 'salary')
            current_user_id: ID текущего пользователя (для фильтрации доступа)
            current_user_role: Роль текущего пользователя (для фильтрации доступа)
            
        Returns:
            Список словарей с данными сотрудников:
            - employee_id, employee_name, role
            - profit_cents (принесенная прибыль)
            - revenue_cents (выручка)
            - orders_count (количество заявок)
            - salary_accrued_cents (начислено)
            - salary_paid_cents (выплачено)
            - salary_owed_cents (к выплате)
            - rank (место в рейтинге)
        """
        normalized_from = _normalize_date_iso(date_from)
        normalized_to = _normalize_date_iso(date_to)
        if date_from and not normalized_from:
            raise ValidationError("Некорректная дата date_from. Используйте YYYY-MM-DD.")
        if date_to and not normalized_to:
            raise ValidationError("Некорректная дата date_to. Используйте YYYY-MM-DD.")
        date_from = normalized_from
        date_to = normalized_to

        # Определяем фильтры по правам доступа
        access_conditions = []
        access_params = []
        
        if _is_master_role(current_user_role):
            # Мастер видит только себя
            employee_info = SalaryDashboardService.get_employee_id_by_user(current_user_id, current_user_role or 'master')
            if not employee_info:
                return []  # Мастер не найден
            
            employee_id, employee_role = employee_info
            access_conditions.append("(e.role = ? AND e.id = ?)")
            access_params.extend([employee_role, employee_id])
            
        elif _is_manager_role(current_user_role):
            # Менеджер видит всех мастеров + себя (но не других менеджеров)
            manager_info = SalaryDashboardService.get_employee_id_by_user(current_user_id, current_user_role or 'manager')
            manager_id = manager_info[0] if manager_info else None
            
            if manager_id:
                # Видим всех мастеров ИЛИ себя (менеджера)
                access_conditions.append("(e.role = 'master' OR (e.role = 'manager' AND e.id = ?))")
                access_params.append(manager_id)
            else:
                # Если менеджер не найден, видим только мастеров
                access_conditions.append("e.role = 'master'")
                
        elif current_user_role == 'admin':
            # Админ видит всех - без фильтра
            pass
        else:
            # viewer и другие - нет доступа
            return []
        
        # Фильтр по роли (если указан)
        role_filter = ""
        if role:
            role_filter = " AND e.role = ?"
            access_params.append(role)
        
        # Фильтр по датам для начислений: по дате ОПЛАТЫ по заявке (как в личном кабинете),
        # чтобы «Начислено» в списке совпадало с начислениями в кабинете сотрудника.
        # Плейсхолдер __ACCRUAL_PERIOD_FILTER_PLACEHOLDER__ подставится ниже после PRAGMA.
        accrual_period_placeholder = "__ACCRUAL_PERIOD_FILTER_PLACEHOLDER__"

        # Формируем условия для фильтрации по статусу (active=1 или NULL считаем активными)
        status_conditions = []
        if status == 'active':
            status_conditions.append("(active = 1 OR active IS NULL)")
        elif status == 'inactive':
            status_conditions.append("active = 0")

        status_where_masters = " AND " + " AND ".join(status_conditions) if status_conditions else ""
        status_where_managers = " AND " + " AND ".join(status_conditions) if status_conditions else ""

        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()

                # Фильтр начислений по дате:
                # - для заявок — по дате оплаты (payments.payment_date/created_at)
                # - для продаж магазина — по дате продажи (shop_sales.sale_date)
                accrual_period_filter = ""
                accrual_where_for_fallback = ""  # для fallback-блока менеджера: " AND (order_id IN (...) OR shop_sale_id IN (...))"
                if date_from or date_to:
                    cursor.execute("PRAGMA table_info(payments)")
                    pay_cols = [r[1] for r in cursor.fetchall()]
                    kind_filter = " AND (p.kind IS NULL OR p.kind != 'refund')" if 'kind' in pay_cols else ""
                    status_filter = " AND p.status = 'captured'" if 'status' in pay_cols else " AND (p.status IS NULL OR p.status != 'cancelled')"
                    d_from = date_from or '1900-01-01'
                    d_to = date_to or '2099-12-31'
                    orders_in_period_sql = f"""
                            SELECT DISTINCT p.order_id FROM payments p
                            WHERE (p.is_cancelled = 0 OR p.is_cancelled IS NULL)
                            {status_filter}
                            {kind_filter}
                            AND DATE(COALESCE(p.payment_date, p.created_at)) >= DATE('{d_from}')
                            AND DATE(COALESCE(p.payment_date, p.created_at)) <= DATE('{d_to}')
                        """

                    # Проверяем наличие продаж магазина и колонки shop_sale_id в начислениях
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shop_sales'")
                    has_shop_sales = cursor.fetchone() is not None
                    cursor.execute("PRAGMA table_info(salary_accruals)")
                    sa_cols = [r[1] for r in cursor.fetchall()]
                    has_shop_sale_id = 'shop_sale_id' in sa_cols

                    if has_shop_sales and has_shop_sale_id:
                        shop_sales_in_period_sql = f"""
                                SELECT id FROM shop_sales
                                WHERE DATE(sale_date) >= DATE('{d_from}')
                                  AND DATE(sale_date) <= DATE('{d_to}')
                            """
                        accrual_period_filter = (
                            " AND ("
                            "sa.order_id IN (" + orders_in_period_sql + ")"
                            " OR "
                            "sa.shop_sale_id IN (" + shop_sales_in_period_sql + ")"
                            ")"
                        )
                        accrual_where_for_fallback = (
                            " AND ("
                            "order_id IN (" + orders_in_period_sql + ")"
                            " OR "
                            "shop_sale_id IN (" + shop_sales_in_period_sql + ")"
                            ")"
                        )
                    else:
                        accrual_period_filter = " AND sa.order_id IN (" + orders_in_period_sql + ")"
                        accrual_where_for_fallback = " AND order_id IN (" + orders_in_period_sql + ")"

                # Получаем список всех сотрудников с учетом прав доступа
                access_where = " AND " + " AND ".join(access_conditions) if access_conditions else ""

                # SQLite не поддерживает LATERAL, используем подзапросы
                query = f"""
                    WITH employees AS (
                        SELECT id, name, 'master' as role FROM masters WHERE (active = 1 OR active IS NULL){status_where_masters}
                        UNION ALL
                        SELECT id, name, 'manager' as role FROM managers WHERE (active = 1 OR active IS NULL){status_where_managers}
                    ),
                    employee_stats AS (
                        SELECT 
                            e.id as employee_id,
                            e.name as employee_name,
                            e.role,
                            -- Прибыль: сумма прибыли по начислениям за период
                            COALESCE(SUM(sa.profit_cents), 0) as profit_cents,
                            -- Выручка: база начислений по начислениям за период
                            COALESCE(SUM(sa.base_amount_cents), 0) as revenue_cents,
                            -- Количество заявок по начислениям за период
                            COUNT(DISTINCT CASE 
                                WHEN sa.amount_cents > 0 THEN sa.order_id
                                ELSE NULL
                            END) as orders_count,
                            -- Начислено зарплаты
                            COALESCE(SUM(sa.amount_cents), 0) as salary_accrued_cents,
                            -- Выплачено (из salary_payments) - плейсхолдер будет заменен
                            COALESCE((
                                SELECT SUM(amount_cents) 
                                FROM salary_payments sp
                                WHERE sp.user_id = e.id AND sp.role = e.role
                                __PAYMENT_DATE_FILTER_PLACEHOLDER__
                            ), 0) as salary_paid_cents
                            ,
                            -- Премии (salary_bonuses)
                            COALESCE((
                                SELECT SUM(amount_cents)
                                FROM salary_bonuses sb
                                WHERE sb.user_id = e.id AND sb.role = e.role
                                __BONUS_DATE_FILTER_PLACEHOLDER__
                            ), 0) as salary_bonuses_cents
                            ,
                            -- Штрафы (salary_fines)
                            COALESCE((
                                SELECT SUM(amount_cents)
                                FROM salary_fines sf
                                WHERE sf.user_id = e.id AND sf.role = e.role
                                __FINE_DATE_FILTER_PLACEHOLDER__
                            ), 0) as salary_fines_cents
                        FROM employees e
                        LEFT JOIN salary_accruals sa ON sa.user_id = e.id AND sa.role = e.role {accrual_period_placeholder}
                        WHERE 1=1 {access_where} {role_filter}
                        GROUP BY e.id, e.name, e.role
                    )
                    SELECT 
                        employee_id,
                        employee_name,
                        role,
                        profit_cents,
                        revenue_cents,
                        orders_count,
                        salary_accrued_cents,
                        salary_paid_cents,
                        salary_bonuses_cents,
                        salary_fines_cents,
                        (
                            (SELECT COALESCE(SUM(sa2.amount_cents), 0) FROM salary_accruals sa2 WHERE sa2.user_id = employee_stats.employee_id AND sa2.role = employee_stats.role)
                            + (SELECT COALESCE(SUM(sb2.amount_cents), 0) FROM salary_bonuses sb2 WHERE sb2.user_id = employee_stats.employee_id AND sb2.role = employee_stats.role)
                            - (SELECT COALESCE(SUM(sf2.amount_cents), 0) FROM salary_fines sf2 WHERE sf2.user_id = employee_stats.employee_id AND sf2.role = employee_stats.role)
                            - (SELECT COALESCE(SUM(sp2.amount_cents), 0) FROM salary_payments sp2 WHERE sp2.user_id = employee_stats.employee_id AND sp2.role = employee_stats.role)
                        ) as salary_owed_cents
                    FROM employee_stats
                    ORDER BY 
                        CASE ?
                            WHEN 'profit' THEN profit_cents
                            WHEN 'revenue' THEN revenue_cents
                            WHEN 'orders' THEN orders_count
                            WHEN 'salary' THEN salary_accrued_cents
                            ELSE profit_cents
                        END DESC
                """
                
                # Подготавливаем параметры
                # Для salary_paid_cents нужны параметры дат (если указаны)
                # Но SQLite не поддерживает параметры в подзапросах корректно, поэтому используем прямую подстановку дат
                # (безопасно, так как это даты, не пользовательский ввод напрямую)
                payment_date_filter_str = ""
                if date_from or date_to:
                    payment_date_filter_str = f" AND DATE(sp.payment_date) >= DATE('{date_from or '1900-01-01'}') AND DATE(sp.payment_date) <= DATE('{date_to or '2099-12-31'}')"
                bonus_date_filter_str = ""
                if date_from or date_to:
                    bonus_date_filter_str = f" AND DATE(sb.bonus_date) >= DATE('{date_from or '1900-01-01'}') AND DATE(sb.bonus_date) <= DATE('{date_to or '2099-12-31'}')"
                fine_date_filter_str = ""
                if date_from or date_to:
                    fine_date_filter_str = f" AND DATE(sf.fine_date) >= DATE('{date_from or '1900-01-01'}') AND DATE(sf.fine_date) <= DATE('{date_to or '2099-12-31'}')"
                
                # Заменяем плейсхолдер в запросе (используем строку, которая точно не встретится в SQL)
                query = query.replace("__PAYMENT_DATE_FILTER_PLACEHOLDER__", payment_date_filter_str)
                query = query.replace("__BONUS_DATE_FILTER_PLACEHOLDER__", bonus_date_filter_str)
                query = query.replace("__FINE_DATE_FILTER_PLACEHOLDER__", fine_date_filter_str)
                query = query.replace("__ACCRUAL_PERIOD_FILTER_PLACEHOLDER__", accrual_period_filter)

                # Собираем все параметры в правильном порядке (даты периода встроены в запрос)
                all_params = access_params + [sort_by]
                
                cursor.execute(query, all_params)
                employees = [dict(row) for row in cursor.fetchall()]

                # Выручка в списке: не SUM(base_amount_cents) по строкам начислений (это база услуг/товаров),
                # а сумма оплат по заявкам с датой в периоде — по одному разу на заявку + продажи магазина.
                # Совпадает с карточкой сотрудника (разбиение по оплатам) и отчётом get_salary_report.
                rev_by_employee: Dict[Tuple[int, str], int] = {}
                if accrual_period_filter.strip():
                    cursor.execute("PRAGMA table_info(payments)")
                    _pay_cols = [r[1] for r in cursor.fetchall()]
                    _kind_f = " AND (p.kind IS NULL OR p.kind != 'refund')" if "kind" in _pay_cols else ""
                    _status_f = (
                        " AND p.status = 'captured'"
                        if "status" in _pay_cols
                        else " AND (p.status IS NULL OR p.status != 'cancelled')"
                    )
                    _d_from = date_from or "1900-01-01"
                    _d_to = date_to or "2099-12-31"
                    if "kind" in _pay_cols:
                        _sum_expr = (
                            "CAST(COALESCE(SUM(CASE WHEN p.kind = 'refund' THEN -p.amount ELSE p.amount END), 0) * 100 AS INTEGER)"
                        )
                    else:
                        _sum_expr = "CAST(COALESCE(SUM(p.amount), 0) * 100 AS INTEGER)"
                    _pay_sub = f"""(
                        SELECT {_sum_expr}
                        FROM payments p
                        WHERE p.order_id = sa.order_id
                          AND (p.is_cancelled = 0 OR p.is_cancelled IS NULL)
                          {_status_f}
                          {_kind_f}
                          AND DATE(COALESCE(p.payment_date, p.created_at)) >= DATE('{_d_from}')
                          AND DATE(COALESCE(p.payment_date, p.created_at)) <= DATE('{_d_to}')
                    )"""
                    _q_orders = f"""
                        SELECT sa.user_id, sa.role, sa.order_id, {_pay_sub} AS rev_cents
                        FROM salary_accruals sa
                        WHERE 1=1 {accrual_period_filter}
                          AND sa.order_id IS NOT NULL
                        GROUP BY sa.user_id, sa.role, sa.order_id
                    """
                    cursor.execute(_q_orders)
                    for _r in cursor.fetchall():
                        _k = (int(_r[0]), str(_r[1]))
                        rev_by_employee[_k] = rev_by_employee.get(_k, 0) + int(_r[3] or 0)

                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='shop_sales'"
                    )
                    if cursor.fetchone():
                        cursor.execute("PRAGMA table_info(salary_accruals)")
                        if "shop_sale_id" in [x[1] for x in cursor.fetchall()]:
                            _q_shop = f"""
                                SELECT sa.user_id, sa.role, sa.shop_sale_id,
                                    CAST(ROUND(COALESCE(
                                        (SELECT ss.total_amount FROM shop_sales ss WHERE ss.id = sa.shop_sale_id),
                                        0
                                    ) * 100) AS INTEGER) AS rev_cents
                                FROM salary_accruals sa
                                WHERE 1=1 {accrual_period_filter}
                                  AND sa.shop_sale_id IS NOT NULL
                                GROUP BY sa.user_id, sa.role, sa.shop_sale_id
                            """
                            cursor.execute(_q_shop)
                            for _r in cursor.fetchall():
                                _k = (int(_r[0]), str(_r[1]))
                                rev_by_employee[_k] = rev_by_employee.get(_k, 0) + int(_r[3] or 0)

                    for _emp in employees:
                        _ek = (int(_emp["employee_id"]), str(_emp["role"]))
                        _emp["revenue_cents"] = rev_by_employee.get(_ek, 0)
                
                # Гарантируем, что текущий менеджер всегда видит себя в списке (на случай сбоя фильтра/привязки)
                if _is_manager_role(current_user_role):
                    manager_info = SalaryDashboardService.get_employee_id_by_user(current_user_id, current_user_role or 'manager')
                    if manager_info:
                        manager_id_val = manager_info[0]
                        if not any((e.get('employee_id') == manager_id_val and e.get('role') == 'manager') for e in employees):
                            cursor.execute(
                                "SELECT id, name, 'manager' as role FROM managers WHERE id = ?",
                                (manager_id_val,),
                            )
                            row = cursor.fetchone()
                            if row:
                                mid, mname, _ = row
                                cursor.execute(
                                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_accruals WHERE user_id = ? AND role = 'manager'" + accrual_where_for_fallback,
                                    (mid,),
                                )
                                accrued = (cursor.fetchone() or (0,))[0]
                                bonus_date_f = f" AND DATE(bonus_date) >= DATE('{date_from or '1900-01-01'}') AND DATE(bonus_date) <= DATE('{date_to or '2099-12-31'}')" if (date_from or date_to) else ""
                                fine_date_f = f" AND DATE(fine_date) >= DATE('{date_from or '1900-01-01'}') AND DATE(fine_date) <= DATE('{date_to or '2099-12-31'}')" if (date_from or date_to) else ""
                                payment_date_f = f" AND DATE(payment_date) >= DATE('{date_from or '1900-01-01'}') AND DATE(payment_date) <= DATE('{date_to or '2099-12-31'}')" if (date_from or date_to) else ""
                                cursor.execute(
                                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_bonuses WHERE user_id = ? AND role = 'manager'" + bonus_date_f,
                                    (mid,),
                                )
                                bonuses = (cursor.fetchone() or (0,))[0]
                                cursor.execute(
                                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_fines WHERE user_id = ? AND role = 'manager'" + fine_date_f,
                                    (mid,),
                                )
                                fines = (cursor.fetchone() or (0,))[0]
                                cursor.execute(
                                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_payments WHERE user_id = ? AND role = 'manager'" + payment_date_f,
                                    (mid,),
                                )
                                paid = (cursor.fetchone() or (0,))[0]
                                # «К выплате» — общий долг за всё время (как в основной таблице)
                                cursor.execute(
                                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_accruals WHERE user_id = ? AND role = 'manager'",
                                    (mid,),
                                )
                                o_acc = (cursor.fetchone() or (0,))[0]
                                cursor.execute(
                                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_bonuses WHERE user_id = ? AND role = 'manager'",
                                    (mid,),
                                )
                                o_bon = (cursor.fetchone() or (0,))[0]
                                cursor.execute(
                                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_fines WHERE user_id = ? AND role = 'manager'",
                                    (mid,),
                                )
                                o_fin = (cursor.fetchone() or (0,))[0]
                                cursor.execute(
                                    "SELECT COALESCE(SUM(amount_cents), 0) FROM salary_payments WHERE user_id = ? AND role = 'manager'",
                                    (mid,),
                                )
                                o_pay = (cursor.fetchone() or (0,))[0]
                                owed = o_acc + o_bon - o_fin - o_pay
                                emp_row = {
                                    'employee_id': mid,
                                    'employee_name': mname,
                                    'role': 'manager',
                                    'profit_cents': 0,
                                    'revenue_cents': 0,
                                    'orders_count': 0,
                                    'salary_accrued_cents': accrued,
                                    'salary_paid_cents': paid,
                                    'salary_bonuses_cents': bonuses,
                                    'salary_fines_cents': fines,
                                    'salary_owed_cents': owed,
                                }
                                if accrual_period_filter.strip():
                                    emp_row['revenue_cents'] = rev_by_employee.get((mid, 'manager'), 0)
                                employees.append(emp_row)
                
                _sort_key_fn = {
                    'profit': lambda e: e.get('profit_cents', 0),
                    'revenue': lambda e: e.get('revenue_cents', 0),
                    'orders': lambda e: e.get('orders_count', 0),
                    'salary': lambda e: e.get('salary_accrued_cents', 0),
                }.get(sort_by, lambda e: e.get('profit_cents', 0))
                employees.sort(key=_sort_key_fn, reverse=True)

                # Добавляем рейтинг (место в топе)
                for idx, employee in enumerate(employees, start=1):
                    employee['rank'] = idx
                
                return employees
                
        except Exception as e:
            logger.error(f"Ошибка при получении списка сотрудников: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при получении списка сотрудников: {e}")
    
    @staticmethod
    @handle_service_error
    def get_employee_dashboard(
        employee_id: int,
        role: str,  # 'master' или 'manager'
        period: str = 'month',  # 'today', 'yesterday', 'week', 'month', 'year', 'custom'
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict:
        """
        Возвращает данные для дашборда сотрудника.
        
        Args:
            employee_id: ID сотрудника
            role: Роль сотрудника
            period: Период ('today', 'yesterday', 'week', 'month', 'year', 'custom')
            date_from: Начало периода (для 'custom')
            date_to: Конец периода (для 'custom')
            
        Returns:
            Словарь с данными:
            - accruals_by_period (начисления по периодам)
            - payments_summary (выплаты)
            - bonuses_fines (премии и штрафы)
            - charts_data (данные для графиков)
            - rating_data (позиция в рейтинге)
        """
        # Определяем даты периода
        # Важно: используем время приложения (по умолчанию Москва), а не локальное время сервера
        today = get_moscow_now().date()
        if period in ('today',):
            date_from = date_to = today.isoformat()
        elif period in ('yesterday',):
            yesterday = today - timedelta(days=1)
            date_from = date_to = yesterday.isoformat()
        elif period in ('day_before_yesterday',):
            dby = today - timedelta(days=2)
            date_from = date_to = dby.isoformat()
        elif period in ('week', '7days'):
            date_from = (today - timedelta(days=7)).isoformat()
            date_to = today.isoformat()
        elif period in ('month', '30days'):
            date_from = (today - timedelta(days=30)).isoformat()
            date_to = today.isoformat()
        elif period == 'quarter':
            date_from = (today - timedelta(days=90)).isoformat()
            date_to = today.isoformat()
        elif period == 'half_year':
            date_from = (today - timedelta(days=180)).isoformat()
            date_to = today.isoformat()
        elif period == 'last_month':
            first_this_month = today.replace(day=1)
            last_month_end = first_this_month - timedelta(days=1)
            date_from = last_month_end.replace(day=1).isoformat()
            date_to = last_month_end.isoformat()
        elif period == 'year':
            date_from = (today - timedelta(days=365)).isoformat()
            date_to = today.isoformat()
        elif period == 'ytd':
            date_from = today.replace(month=1, day=1).isoformat()
            date_to = today.isoformat()
        # Для 'custom' используем переданные date_from и date_to
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Начисления за период: фильтруем по дате ОПЛАТЫ (payment_date),
                # чтобы "Сегодня" показывало начисления по платежам, сделанным сегодня.
                accruals_query = """
                    SELECT 
                        sa.id,
                        sa.order_id,
                        sa.role,
                        sa.amount_cents,
                        sa.base_amount_cents,
                        sa.profit_cents,
                        sa.rule_type,
                        sa.rule_value,
                        sa.calculated_from,
                        sa.created_at,
                        o.order_id as order_uuid,
                        o.order_id as order_number
                    FROM salary_accruals sa
                    LEFT JOIN orders o ON o.id = sa.order_id
                    WHERE sa.user_id = ? AND sa.role = ?
                """
                accruals_params: List[Any] = [employee_id, role]
                cursor.execute("PRAGMA table_info(salary_accruals)")
                sa_cols = [r[1] for r in cursor.fetchall()]
                has_shop_sale_id = 'shop_sale_id' in sa_cols
                if has_shop_sale_id:
                    accruals_query = accruals_query.replace(
                        "sa.order_id,\n                        sa.role,",
                        "sa.order_id,\n                        sa.shop_sale_id,\n                        sa.role,"
                    )
                # Период: начисления по заявкам (оплаты в периоде) ИЛИ по продажам магазина (sale_date в периоде)
                if date_from and date_to:
                    cursor.execute("PRAGMA table_info(payments)")
                    pay_cols = [r[1] for r in cursor.fetchall()]
                    kind_filter = " AND (p.kind IS NULL OR p.kind != 'refund')" if 'kind' in pay_cols else ""
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shop_sales'")
                    has_shop_sales = cursor.fetchone() is not None
                    if has_shop_sales and has_shop_sale_id:
                        accruals_query += """
                        AND (
                            sa.order_id IN (
                                SELECT DISTINCT p.order_id FROM payments p
                                WHERE p.order_id = sa.order_id
                                  AND (p.is_cancelled = 0 OR p.is_cancelled IS NULL)
                                  """ + kind_filter + """
                                  AND DATE(COALESCE(p.payment_date, p.created_at)) >= DATE(?)
                                  AND DATE(COALESCE(p.payment_date, p.created_at)) <= DATE(?)
                            )
                            OR sa.shop_sale_id IN (
                                SELECT id FROM shop_sales
                                WHERE DATE(sale_date) >= DATE(?) AND DATE(sale_date) <= DATE(?)
                            )
                        )
                        """
                        accruals_params.extend([date_from, date_to, date_from, date_to])
                    else:
                        accruals_query += f"""
                        AND sa.order_id IN (
                            SELECT DISTINCT p.order_id FROM payments p
                            WHERE p.order_id = sa.order_id
                              AND (p.is_cancelled = 0 OR p.is_cancelled IS NULL)
                              {kind_filter}
                              AND DATE(COALESCE(p.payment_date, p.created_at)) >= DATE(?)
                              AND DATE(COALESCE(p.payment_date, p.created_at)) <= DATE(?)
                        )
                    """
                        accruals_params.extend([date_from, date_to])
                accruals_query += " ORDER BY sa.created_at DESC"
                
                logger.info(f"Executing accruals query: {accruals_query[:100]}... with params: {accruals_params}")
                cursor.execute(accruals_query, accruals_params)
                accruals = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Found {len(accruals)} accruals for employee {employee_id} ({role})")

                # Детализация начислений по оплатам:
                # Итоговая сумма начисления уже посчитана в БД (доля от прибыли/выручки позиций или заказа).
                # Чтобы не завысить цифры, разбиваем accrual_amount_cents пропорционально суммам оплат:
                # иначе для rule_type=percent ошибочно считали бы payment × rule_value%, хотя расчёт в SalaryService
                # идёт от прибыли строки, а не от платежа (при крупной оплате получалось вроде 2500 ₽ вместо 1000 ₽).
                if accruals:
                    order_ids = sorted({int(a['order_id']) for a in accruals if a.get('order_id')})
                    payments_by_order: Dict[int, List[Dict[str, Any]]] = {}

                    if order_ids:
                        placeholders = ",".join("?" for _ in order_ids)
                        cursor.execute("PRAGMA table_info(payments)")
                        pay_cols = [r[1] for r in cursor.fetchall()]
                        has_kind = 'kind' in pay_cols
                        has_status = 'status' in pay_cols
                        kind_filter = " AND (kind IS NULL OR kind != 'refund')" if has_kind else ""
                        status_filter = " AND status = 'captured'" if has_status else " AND (status IS NULL OR status != 'cancelled')"
                        order_payments_query = f"""
                            SELECT id, order_id, amount, payment_date, payment_type, comment, created_at
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            {status_filter}
                            {kind_filter}
                        """
                        # Важно: берём ВСЕ оплаты заявки (без фильтра периода).
                        # Период применяется ниже к уже разложенным строкам начислений по payment_date.
                        # Иначе при today/7days доли завышаются, т.к. делим на неполный набор оплат.
                        order_payments_params: List[Any] = list(order_ids)
                        order_payments_query += " ORDER BY COALESCE(payment_date, created_at) ASC, id ASC"

                        cursor.execute(order_payments_query, order_payments_params)
                        for p in cursor.fetchall():
                            p_dict = dict(p)
                            p_order_id = int(p_dict.get('order_id') or 0)
                            if p_order_id <= 0:
                                continue
                            payments_by_order.setdefault(p_order_id, []).append(p_dict)

                    split_accruals: List[Dict[str, Any]] = []
                    for accrual in accruals:
                        try:
                            order_id_val = int(accrual.get('order_id') or 0)
                        except (TypeError, ValueError):
                            order_id_val = 0
                        order_payments = payments_by_order.get(order_id_val, [])

                        accrual_amount_cents = int(accrual.get('amount_cents') or 0)
                        if not order_payments or accrual_amount_cents == 0:
                            accrual_row = dict(accrual)
                            accrual_row['is_payment_split'] = False
                            split_accruals.append(accrual_row)
                            continue

                        rule_type = accrual.get('rule_type') or 'percent'
                        n_pay = len(order_payments)
                        _allocated_split = 0
                        total_payments_amount = sum(
                            float(p.get('amount') or 0) for p in order_payments
                        )

                        for _pi, payment in enumerate(order_payments):
                            amount_float = float(payment.get('amount') or 0)
                            payment_amount_cents = int(round(amount_float * 100))

                            is_last_payment = _pi == n_pay - 1
                            # Доля начисления, относимая к этой оплате: пропорционально её сумме;
                            # на последней — остаток, чтобы сумма строк точно равнялась amount_cents из БД.
                            if rule_type in ('percent', 'fixed'):
                                if is_last_payment:
                                    salary_from_payment_cents = max(
                                        0, accrual_amount_cents - _allocated_split
                                    )
                                elif total_payments_amount > 0:
                                    salary_from_payment_cents = int(
                                        round(
                                            accrual_amount_cents
                                            * (amount_float / total_payments_amount)
                                        )
                                    )
                                else:
                                    salary_from_payment_cents = 0
                            else:
                                salary_from_payment_cents = 0

                            if salary_from_payment_cents <= 0:
                                continue

                            _allocated_split += salary_from_payment_cents

                            row = dict(accrual)
                            row['is_payment_split'] = True
                            row['payment_id'] = payment.get('id')
                            row['payment_date'] = payment.get('payment_date') or payment.get('created_at')
                            row['payment_type'] = payment.get('payment_type')
                            row['payment_comment'] = payment.get('comment')
                            row['payment_amount_cents'] = payment_amount_cents
                            row['amount_cents'] = salary_from_payment_cents
                            # Для табличного отображения в колонке "База (прибыль)"
                            # показываем именно сумму конкретной оплаты.
                            row['profit_cents'] = payment_amount_cents
                            row['base_amount_cents'] = payment_amount_cents
                            split_accruals.append(row)

                    # Дополнительно группируем по оплате + правилу, чтобы не дублировать строки
                    # (например, если начисление пришло из нескольких источников с одинаковым %).
                    grouped_payment_rows: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
                    grouped_result: List[Dict[str, Any]] = []
                    for row in split_accruals:
                        if not row.get('is_payment_split'):
                            grouped_result.append(row)
                            continue

                        key = (
                            row.get('order_id'),
                            row.get('payment_id'),
                            row.get('rule_type'),
                            float(row.get('rule_value') or 0),
                            row.get('role'),
                            row.get('user_id'),
                        )
                        if key not in grouped_payment_rows:
                            grouped_payment_rows[key] = dict(row)
                        else:
                            grouped_payment_rows[key]['amount_cents'] = int(grouped_payment_rows[key].get('amount_cents') or 0) + int(row.get('amount_cents') or 0)

                    grouped_result.extend(grouped_payment_rows.values())
                    if date_from and date_to:
                        # Для строк, разложенных по оплатам, фильтруем строго по дате этой оплаты.
                        # Это корректно работает для "переоткрыли старую заявку и снова закрыли":
                        # в период попадает только доля начисления, относящаяся к оплатам периода.
                        filtered_rows: List[Dict[str, Any]] = []
                        for row in grouped_result:
                            if row.get('is_payment_split'):
                                payment_date = str(row.get('payment_date') or '').strip()
                                payment_day = payment_date[:10] if payment_date else ''
                                if payment_day and date_from <= payment_day <= date_to:
                                    filtered_rows.append(row)
                            else:
                                filtered_rows.append(row)
                        grouped_result = filtered_rows

                    # Сортировка по дате (сначала новые), затем по id
                    def _sort_key(row):
                        dt = row.get('payment_date') or row.get('created_at') or ''
                        return (str(dt) if dt else '', int(row.get('id') or 0))
                    grouped_result.sort(key=_sort_key, reverse=True)

                    accruals = grouped_result
                    logger.info(f"Accruals split/grouped by payments: {len(accruals)} rows")
                
                # Выплаты за период
                payments_query = """
                    SELECT 
                        id,
                        amount_cents,
                        payment_date,
                        period_start,
                        period_end,
                        payment_type,
                        comment
                    FROM salary_payments
                    WHERE user_id = ? AND role = ?
                """
                payments_params = [employee_id, role]
                
                # Сравниваем по первым 10 символам (YYYY-MM-DD), чтобы учитывались и дата, и datetime
                if date_from:
                    payments_query += " AND SUBSTR(TRIM(COALESCE(payment_date::text, '')), 1, 10) >= ?"
                    payments_params.append(date_from[:10] if len(date_from) >= 10 else date_from)
                if date_to:
                    payments_query += " AND SUBSTR(TRIM(COALESCE(payment_date::text, '')), 1, 10) <= ?"
                    payments_params.append(date_to[:10] if len(date_to) >= 10 else date_to)
                
                payments_query += " ORDER BY payment_date DESC, id DESC"
                
                try:
                    cursor.execute(payments_query, payments_params)
                    payments = [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Таблица salary_payments может еще не существовать
                    payments = []
                
                # Премии и штрафы за период
                bonuses_query = """
                    SELECT 
                        id,
                        amount_cents,
                        reason,
                        bonus_date as date,
                        'bonus' as type
                    FROM salary_bonuses
                    WHERE user_id = ? AND role = ?
                """
                bonuses_params = [employee_id, role]
                
                if date_from:
                    bonuses_query += " AND DATE(bonus_date) >= DATE(?)"
                    bonuses_params.append(date_from)
                if date_to:
                    bonuses_query += " AND DATE(bonus_date) <= DATE(?)"
                    bonuses_params.append(date_to)
                
                fines_query = """
                    SELECT 
                        id,
                        amount_cents,
                        reason,
                        fine_date as date,
                        'fine' as type
                    FROM salary_fines
                    WHERE user_id = ? AND role = ?
                """
                fines_params = [employee_id, role]
                
                if date_from:
                    fines_query += " AND DATE(fine_date) >= DATE(?)"
                    fines_params.append(date_from)
                if date_to:
                    fines_query += " AND DATE(fine_date) <= DATE(?)"
                    fines_params.append(date_to)
                
                bonuses_query += " ORDER BY bonus_date DESC, id DESC"
                fines_query += " ORDER BY fine_date DESC, id DESC"
                
                bonuses = []
                fines = []
                try:
                    cursor.execute(bonuses_query, bonuses_params)
                    bonuses = [dict(row) for row in cursor.fetchall()]
                    
                    cursor.execute(fines_query, fines_params)
                    fines = [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Таблицы могут еще не существовать
                    pass
                
                # Итоги
                total_accrued = sum(a.get('amount_cents', 0) for a in accruals)
                total_paid = sum(p.get('amount_cents', 0) for p in payments)
                total_bonuses = sum(b.get('amount_cents', 0) for b in bonuses)
                total_fines = sum(f.get('amount_cents', 0) for f in fines)
                # "К выплате" не должен уходить в минус из-за выплат, сделанных сегодня за долги прошлых периодов.
                # Поэтому для показателя "к выплате" используем общий долг (с накоплением), а период оставляем для списков.
                total_owed_period = total_accrued + total_bonuses - total_fines - total_paid

                # Общий долг (без фильтра по периоду)
                overall_accrued = 0
                overall_paid = 0
                overall_bonuses = 0
                overall_fines = 0
                try:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(amount_cents), 0)
                        FROM salary_accruals
                        WHERE user_id = ? AND role = ?
                        """,
                        (employee_id, role),
                    )
                    overall_accrued = int(cursor.fetchone()[0] or 0)
                except Exception:
                    overall_accrued = 0
                try:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(amount_cents), 0)
                        FROM salary_payments
                        WHERE user_id = ? AND role = ?
                        """,
                        (employee_id, role),
                    )
                    overall_paid = int(cursor.fetchone()[0] or 0)
                except Exception:
                    overall_paid = 0
                try:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(amount_cents), 0)
                        FROM salary_bonuses
                        WHERE user_id = ? AND role = ?
                        """,
                        (employee_id, role),
                    )
                    overall_bonuses = int(cursor.fetchone()[0] or 0)
                except Exception:
                    overall_bonuses = 0
                try:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(amount_cents), 0)
                        FROM salary_fines
                        WHERE user_id = ? AND role = ?
                        """,
                        (employee_id, role),
                    )
                    overall_fines = int(cursor.fetchone()[0] or 0)
                except Exception:
                    overall_fines = 0

                overall_owed = overall_accrued + overall_bonuses - overall_fines - overall_paid

                # Сколько можно зарегистрировать выплатой сейчас: обычно max(0, общий_долг).
                # Если общий баланс 0 из‑за старой переплаты, а за период виден остаток (110−107.20),
                # без этого поля кнопка «Выплатить» и register_payment блокируют добивочную сумму.
                payable_cents = max(0, int(overall_owed))
                if payable_cents <= 0 and int(total_owed_period) > 0:
                    payable_cents = int(total_owed_period)
                
                return {
                    'employee_id': employee_id,
                    'role': role,
                    'period': period,
                    'date_from': date_from,
                    'date_to': date_to,
                    'accruals': accruals,
                    'payments': payments,
                    'bonuses': bonuses,
                    'fines': fines,
                    'totals': {
                        'accrued_cents': total_accrued,
                        'paid_cents': total_paid,
                        'bonuses_cents': total_bonuses,
                        'fines_cents': total_fines,
                        # Показываем "к выплате" как общий долг
                        'owed_cents': overall_owed,
                        'overall_owed_cents': overall_owed,
                        # Дополнительно: долг в рамках выбранного периода (может быть отрицательным)
                        'period_owed_cents': total_owed_period,
                        'payable_cents': payable_cents,
                    }
                }
                
        except Exception as e:
            logger.error(f"Ошибка при получении дашборда сотрудника {employee_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при получении дашборда: {e}")

    @staticmethod
    @handle_service_error
    def get_salary_debts(role: Optional[str] = None, status: Optional[str] = 'active') -> Dict[str, Any]:
        """
        Возвращает список долгов сотрудников (начислено + премии - штрафы - выплаты).
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()

                status_conditions = []
                if status == 'active':
                    status_conditions.append("(active = 1 OR active IS NULL)")
                elif status == 'inactive':
                    status_conditions.append("active = 0")
                status_where_masters = " AND " + " AND ".join(status_conditions) if status_conditions else ""
                status_where_managers = " AND " + " AND ".join(status_conditions) if status_conditions else ""

                role_filter = ""
                params: List[Any] = []
                if role in ['master', 'manager']:
                    role_filter = "WHERE e.role = ?"
                    params.append(role)

                query = f"""
                    WITH employees AS (
                        SELECT id, name, 'master' as role FROM masters WHERE (active = 1 OR active IS NULL){status_where_masters}
                        UNION ALL
                        SELECT id, name, 'manager' as role FROM managers WHERE (active = 1 OR active IS NULL){status_where_managers}
                    ),
                    sums AS (
                        SELECT 
                            e.id as employee_id,
                            e.name as employee_name,
                            e.role,
                            COALESCE((SELECT SUM(amount_cents) FROM salary_accruals sa WHERE sa.user_id = e.id AND sa.role = e.role), 0) as accrued_cents,
                            COALESCE((SELECT SUM(amount_cents) FROM salary_bonuses sb WHERE sb.user_id = e.id AND sb.role = e.role), 0) as bonuses_cents,
                            COALESCE((SELECT SUM(amount_cents) FROM salary_fines sf WHERE sf.user_id = e.id AND sf.role = e.role), 0) as fines_cents,
                            COALESCE((SELECT SUM(amount_cents) FROM salary_payments sp WHERE sp.user_id = e.id AND sp.role = e.role), 0) as paid_cents
                        FROM employees e
                        {role_filter}
                    )
                    SELECT 
                        employee_id,
                        employee_name,
                        role,
                        accrued_cents,
                        bonuses_cents,
                        fines_cents,
                        paid_cents,
                        (accrued_cents + bonuses_cents - fines_cents - paid_cents) as owed_cents
                    FROM sums
                    ORDER BY owed_cents ASC, employee_name
                """

                cursor.execute(query, params)
                rows = [dict(r) for r in cursor.fetchall()]

                total_to_pay = sum(r['owed_cents'] for r in rows if r['owed_cents'] > 0)
                total_debt_company = sum(abs(r['owed_cents']) for r in rows if r['owed_cents'] < 0)

                return {
                    'items': rows,
                    'totals': {
                        'total_to_pay_cents': total_to_pay,
                        'total_debt_company_cents': total_debt_company,
                    }
                }
        except Exception as e:
            logger.error(f"Ошибка при получении долгов по зарплате: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при получении долгов: {e}")

    @staticmethod
    @handle_service_error
    def writeoff_debt(
        user_id: int,
        role: str,
        amount_cents: int,
        reason: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None
    ) -> int:
        """
        Списывает долг сотрудника через запись в премии (без кассы).
        """
        if not user_id or user_id <= 0:
            raise ValidationError("Неверный ID сотрудника")
        if role not in ['master', 'manager']:
            raise ValidationError("Неверная роль сотрудника")
        if not amount_cents or amount_cents <= 0:
            raise ValidationError("Сумма списания должна быть положительной")

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='salary_bonuses'")
                if not cursor.fetchone():
                    raise DatabaseError("Таблица salary_bonuses не существует. Примените миграцию.")

                overall_owed = SalaryDashboardService._get_overall_owed_with_cursor(cursor, user_id, role)
                if overall_owed >= 0:
                    raise ValidationError("У сотрудника нет долга перед компанией")
                max_writeoff = abs(int(overall_owed))
                if amount_cents > max_writeoff:
                    raise ValidationError("Сумма списания больше текущего долга")

                bonus_date = get_moscow_now_str('%Y-%m-%d')
                created_at = get_moscow_now_str()
                reason_text = (reason or "Списание долга").strip()

                cursor.execute('''
                    INSERT INTO salary_bonuses (
                        user_id, role, amount_cents, reason, order_id,
                        bonus_date, created_by_id, created_by_username, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, role, amount_cents, reason_text, None,
                      bonus_date, created_by_id, created_by_username, created_at))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при списании долга: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при списании долга: {e}")
    
    @staticmethod
    @handle_service_error
    def add_bonus(
        user_id: int,
        role: str,
        amount_cents: int,
        reason: str,
        bonus_date: str,
        order_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None
    ) -> int:
        """
        Создает запись о премии.
        
        Args:
            user_id: ID сотрудника (master_id или manager_id)
            role: Роль ('master' или 'manager')
            amount_cents: Сумма премии в копейках
            reason: Причина премии
            bonus_date: Дата премии (YYYY-MM-DD)
            order_id: ID заявки (опционально)
            created_by_id: ID пользователя, создавшего запись
            created_by_username: Имя пользователя
            
        Returns:
            ID созданной записи
        """
        if not user_id or user_id <= 0:
            raise ValidationError("Неверный ID сотрудника")
        if not amount_cents or amount_cents <= 0:
            raise ValidationError("Сумма премии должна быть положительной")
        if not reason or not reason.strip():
            raise ValidationError("Причина премии обязательна")
        if role not in ['master', 'manager']:
            raise ValidationError("Неверная роль сотрудника")
        if bonus_date:
            normalized_bonus_date = _normalize_date_iso(bonus_date)
            if not normalized_bonus_date:
                raise ValidationError("Некорректная дата премии. Используйте YYYY-MM-DD.")
            bonus_date = normalized_bonus_date
        else:
            bonus_date = get_moscow_now().strftime('%Y-%m-%d')
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли таблица salary_bonuses
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='salary_bonuses'")
                if not cursor.fetchone():
                    raise DatabaseError("Таблица salary_bonuses не существует. Примените миграцию.")
                
                created_at = get_moscow_now_str()
                cursor.execute('''
                    INSERT INTO salary_bonuses (
                        user_id, role, amount_cents, reason, order_id,
                        bonus_date, created_by_id, created_by_username, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, role, amount_cents, reason.strip(), order_id,
                      bonus_date, created_by_id, created_by_username, created_at))
                conn.commit()
                
                bonus_id = cursor.lastrowid
                
                # Логируем действие
                try:
                    from app.services.action_log_service import ActionLogService
                    ActionLogService.log_action(
                        user_id=created_by_id,
                        username=created_by_username,
                        action_type='create',
                        entity_type='salary_bonus',
                        entity_id=bonus_id,
                        description=f"Начислена премия {amount_cents / 100:.2f} ₽ сотруднику {user_id} ({role})",
                        details={
                            'employee_id': user_id,
                            'role': role,
                            'amount_cents': amount_cents,
                            'reason': reason.strip(),
                            'bonus_date': bonus_date
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать начисление премии: {e}")
                
                return bonus_id
                
        except Exception as e:
            logger.error(f"Ошибка при начислении премии: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при начислении премии: {e}")
    
    @staticmethod
    @handle_service_error
    def add_fine(
        user_id: int,
        role: str,
        amount_cents: int,
        reason: str,
        fine_date: str,
        order_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None
    ) -> int:
        """
        Создает запись о штрафе.
        
        Args:
            user_id: ID сотрудника (master_id или manager_id)
            role: Роль ('master' или 'manager')
            amount_cents: Сумма штрафа в копейках
            reason: Причина штрафа
            fine_date: Дата штрафа (YYYY-MM-DD)
            order_id: ID заявки (опционально)
            created_by_id: ID пользователя, создавшего запись
            created_by_username: Имя пользователя
            
        Returns:
            ID созданной записи
        """
        if not user_id or user_id <= 0:
            raise ValidationError("Неверный ID сотрудника")
        if not amount_cents or amount_cents <= 0:
            raise ValidationError("Сумма штрафа должна быть положительной")
        if not reason or not reason.strip():
            raise ValidationError("Причина штрафа обязательна")
        if role not in ['master', 'manager']:
            raise ValidationError("Неверная роль сотрудника")
        if fine_date:
            normalized_fine_date = _normalize_date_iso(fine_date)
            if not normalized_fine_date:
                raise ValidationError("Некорректная дата штрафа. Используйте YYYY-MM-DD.")
            fine_date = normalized_fine_date
        else:
            fine_date = get_moscow_now().strftime('%Y-%m-%d')
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли таблица salary_fines
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='salary_fines'")
                if not cursor.fetchone():
                    raise DatabaseError("Таблица salary_fines не существует. Примените миграцию.")
                
                created_at = get_moscow_now_str()
                cursor.execute('''
                    INSERT INTO salary_fines (
                        user_id, role, amount_cents, reason, order_id,
                        fine_date, created_by_id, created_by_username, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, role, amount_cents, reason.strip(), order_id,
                      fine_date, created_by_id, created_by_username, created_at))
                conn.commit()
                
                fine_id = cursor.lastrowid
                
                # Логируем действие
                try:
                    from app.services.action_log_service import ActionLogService
                    ActionLogService.log_action(
                        user_id=created_by_id,
                        username=created_by_username,
                        action_type='create',
                        entity_type='salary_fine',
                        entity_id=fine_id,
                        description=f"Начислен штраф {amount_cents / 100:.2f} ₽ сотруднику {user_id} ({role})",
                        details={
                            'employee_id': user_id,
                            'role': role,
                            'amount_cents': amount_cents,
                            'reason': reason.strip(),
                            'fine_date': fine_date
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать начисление штрафа: {e}")
                
                return fine_id
                
        except Exception as e:
            logger.error(f"Ошибка при начислении штрафа: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при начислении штрафа: {e}")
    
    @staticmethod
    @handle_service_error
    def register_payment(
        user_id: int,
        role: str,
        amount_cents: int,
        payment_date: str,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        payment_type: str = 'salary',  # 'salary', 'bonus', 'advance'
        comment: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None
    ) -> int:
        """
        Регистрирует выплату зарплаты.
        
        Args:
            user_id: ID сотрудника (master_id или manager_id)
            role: Роль ('master' или 'manager')
            amount_cents: Сумма выплаты в копейках
            payment_date: Дата выплаты (YYYY-MM-DD)
            period_start: Начало периода расчета (опционально)
            period_end: Конец периода расчета (опционально)
            payment_type: Тип выплаты ('salary', 'bonus', 'advance')
            comment: Комментарий
            created_by_id: ID пользователя, создавшего запись
            created_by_username: Имя пользователя
            
        Returns:
            ID созданной записи
        """
        if not user_id or user_id <= 0:
            raise ValidationError("Неверный ID сотрудника")
        if not amount_cents or amount_cents <= 0:
            raise ValidationError("Сумма выплаты должна быть положительной")
        if role not in ['master', 'manager']:
            raise ValidationError("Неверная роль сотрудника")
        if payment_type not in ['salary', 'bonus', 'advance']:
            raise ValidationError("Неверный тип выплаты")
        if payment_date:
            normalized_payment_date = _normalize_date_iso(payment_date)
            if not normalized_payment_date:
                raise ValidationError("Некорректная дата выплаты. Используйте YYYY-MM-DD.")
            payment_date = normalized_payment_date
        else:
            payment_date = get_moscow_now().strftime('%Y-%m-%d')
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли таблица salary_payments
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='salary_payments'")
                if not cursor.fetchone():
                    raise DatabaseError("Таблица salary_payments не существует. Примените миграцию.")

                # Защита от дубликата: одна и та же выплата (сотрудник, дата, сумма) не создаётся дважды
                cursor.execute(
                    """
                    SELECT id, created_at FROM salary_payments
                    WHERE user_id = ? AND role = ? AND amount_cents = ? AND payment_date = ?
                    ORDER BY id DESC LIMIT 1
                    """,
                    (user_id, role, amount_cents, payment_date),
                )
                existing = cursor.fetchone()
                if existing:
                    existing_id, existing_created = existing[0], existing[1]
                    try:
                        created_dt = datetime.strptime(existing_created[:19], "%Y-%m-%d %H:%M:%S") if existing_created and len(str(existing_created)) >= 19 else None
                        if created_dt and (get_moscow_now() - created_dt).total_seconds() < 120:
                            logger.info(f"Выплата уже зарегистрирована (id={existing_id}), повтор не создаём")
                            return existing_id
                    except Exception:
                        pass
                    raise ValidationError(
                        "Такая выплата уже есть (та же дата и сумма). Удалите дубликат в БД или измените дату/сумму."
                    )

                # Верхняя граница выплаты: общий долг компании перед сотрудником.
                # Если из‑за переплаты в прошлом общий баланс 0, а за дату выплаты в кабинете
                # виден остаток (начислено за день − выплачено за день) — разрешаем добить эту сумму.
                overall_owed = SalaryDashboardService._get_overall_owed_with_cursor(cursor, user_id, role)
                max_payable = max(0, int(overall_owed))
                if max_payable <= 0:
                    try:
                        day_dash = SalaryDashboardService.get_employee_dashboard(
                            employee_id=user_id,
                            role=role,
                            period="custom",
                            date_from=payment_date,
                            date_to=payment_date,
                        )
                        gap = int(
                            (day_dash.get("totals") or {}).get("period_owed_cents") or 0
                        )
                        if gap > 0:
                            max_payable = gap
                    except Exception as ex:
                        logger.warning(
                            "Не удалось получить остаток за день для выплаты: %s", ex
                        )
                if amount_cents > max_payable:
                    raise ValidationError(
                        "Сумма выплаты не может превышать доступную к выплате сумму "
                        f"(максимум {max_payable / 100:.2f} ₽ по текущему балансу и периоду)."
                    )
                
                created_at = get_moscow_now_str()
                
                # Проверяем, есть ли поле cash_transaction_id в таблице
                cursor.execute("PRAGMA table_info(salary_payments)")
                columns = [row[1] for row in cursor.fetchall()]
                has_cash_transaction_id = 'cash_transaction_id' in columns
                
                if has_cash_transaction_id:
                    # Сначала создаем запись без cash_transaction_id, потом обновим
                    cursor.execute('''
                        INSERT INTO salary_payments (
                            user_id, role, amount_cents, payment_date,
                            period_start, period_end, payment_type, comment,
                            created_by_id, created_by_username, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, role, amount_cents, payment_date,
                          period_start, period_end, payment_type, comment,
                          created_by_id, created_by_username, created_at))
                    payment_id = cursor.lastrowid
                else:
                    # Старая версия таблицы без cash_transaction_id
                    cursor.execute('''
                        INSERT INTO salary_payments (
                            user_id, role, amount_cents, payment_date,
                            period_start, period_end, payment_type, comment,
                            created_by_id, created_by_username, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, role, amount_cents, payment_date,
                          period_start, period_end, payment_type, comment,
                          created_by_id, created_by_username, created_at))
                    payment_id = cursor.lastrowid
                    # Если cash_transaction_id не поддерживается, пропускаем его сохранение
                    cash_transaction_id = None
                conn.commit()  # Освобождаем блокировку БД перед вызовом create_transaction (иначе "database is locked")
                
                # Создаем кассовую операцию (расход из кассы) — в отдельном соединении
                try:
                    from app.services.finance_service import FinanceService
                    
                    amount = amount_cents / 100.0

                    # Подбираем статью для кассы в зависимости от типа выплаты
                    if payment_type == 'bonus':
                        category_name = 'Премии сотрудникам'
                    elif payment_type == 'advance':
                        category_name = 'Авансы по зарплате'
                    else:
                        category_name = 'Выплата зарплаты'

                    # Получаем имя сотрудника для описания
                    employee_name = None
                    try:
                        if role == 'master':
                            cursor.execute('SELECT name FROM masters WHERE id = ?', (user_id,))
                        else:
                            cursor.execute('SELECT name FROM managers WHERE id = ?', (user_id,))
                        row = cursor.fetchone()
                        if row:
                            employee_name = row[0]
                    except Exception:
                        employee_name = None

                    role_label = 'мастер' if role == 'master' else 'менеджер'
                    employee_label = f"{employee_name} ({role_label})" if employee_name else f"{role_label} {user_id}"

                    # Делаем описание детерминированным, чтобы не плодить дубли
                    salary_payment_tag = f"salary_payment#{payment_id}"

                    description_parts = [salary_payment_tag, category_name, f"сотруднику {employee_label}"]
                    if period_start or period_end:
                        description_parts.append(
                            f"за период {period_start or '…'} — {period_end or '…'}"
                        )
                    if comment:
                        description_parts.append(comment)
                    description = ". ".join(part for part in description_parts if part)

                    # Защита от дубля для зарплатных выплат (cash_transactions.payment_id зарезервирован под payments.id)
                    should_create_cash_tx = True
                    try:
                        cursor.execute(
                            """
                            SELECT id FROM cash_transactions
                            WHERE transaction_type = 'expense'
                              AND transaction_date = ?
                              AND amount = ?
                              AND description = ?
                            LIMIT 1
                            """,
                            (payment_date, amount, description),
                        )
                        if cursor.fetchone():
                            should_create_cash_tx = False
                    except Exception:
                        # если проверка не удалась — не блокируем создание
                        should_create_cash_tx = True

                    cash_transaction_id = None
                    if should_create_cash_tx:
                        # Расход из кассы: transaction_type='expense'
                        cash_transaction_id = FinanceService.create_transaction(
                            amount=amount,
                            transaction_type='expense',
                            category_name=category_name,
                            payment_method='cash',
                            description=description,
                            transaction_date=payment_date,
                            payment_id=None,
                            created_by_id=created_by_id,
                            created_by_username=created_by_username,
                            skip_balance_check=True,
                        )
                        
                        # Обновляем salary_payments с cash_transaction_id, если поле существует
                        if has_cash_transaction_id and cash_transaction_id:
                            cursor.execute('''
                                UPDATE salary_payments
                                SET cash_transaction_id = ?
                                WHERE id = ?
                            ''', (cash_transaction_id, payment_id))
                            conn.commit()
                except Exception as e:
                    # Не блокируем регистрацию выплаты, если не удалось создать кассовую операцию
                    logger.error(f"Ошибка при создании кассовой операции для выплаты зарплаты {payment_id}: {e}", exc_info=True)
                
                # Логируем действие
                try:
                    from app.services.action_log_service import ActionLogService
                    ActionLogService.log_action(
                        user_id=created_by_id,
                        username=created_by_username,
                        action_type='create',
                        entity_type='salary_payment',
                        entity_id=payment_id,
                        description=f"Зарегистрирована выплата {amount_cents / 100:.2f} ₽ сотруднику {user_id} ({role})",
                        details={
                            'employee_id': user_id,
                            'role': role,
                            'amount_cents': amount_cents,
                            'payment_date': payment_date,
                            'payment_type': payment_type,
                            'period_start': period_start,
                            'period_end': period_end
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать регистрацию выплаты: {e}")
                
                return payment_id
                
        except Exception as e:
            logger.error(f"Ошибка при регистрации выплаты: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при регистрации выплаты: {e}")

    @staticmethod
    def backfill_missing_salary_cash_transactions(
        date_from: str,
        date_to: str,
    ) -> int:
        """
        Создаёт отсутствующие кассовые операции для выплат зарплаты с cash_transaction_id IS NULL.
        date_from/date_to — фильтр по payment_date (YYYY-MM-DD). Возвращает количество созданных операций.
        """
        from app.services.finance_service import FinanceService

        created = 0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(salary_payments)")
            columns = [c[1] for c in cursor.fetchall()]
            if 'cash_transaction_id' not in columns:
                return 0
            query = """
                SELECT id, user_id, role, amount_cents, payment_date, period_start, period_end, payment_type, comment,
                       created_by_id, created_by_username
                FROM salary_payments
                WHERE cash_transaction_id IS NULL
            """
            params = []
            if date_from:
                query += " AND DATE(payment_date) >= DATE(?)"
                params.append(date_from[:10] if len(date_from) >= 10 else date_from)
            if date_to:
                query += " AND DATE(payment_date) <= DATE(?)"
                params.append(date_to[:10] if len(date_to) >= 10 else date_to)
            query += " ORDER BY payment_date, id"
            cursor.execute(query, params)
            rows = cursor.fetchall()

        for row in rows:
            (payment_id, user_id, role, amount_cents, payment_date, period_start, period_end,
             payment_type, comment, created_by_id, created_by_username) = row
            amount = amount_cents / 100.0
            if payment_type == 'bonus':
                category_name = 'Премии сотрудникам'
            elif payment_type == 'advance':
                category_name = 'Авансы по зарплате'
            else:
                category_name = 'Выплата зарплаты'

            employee_name = None
            try:
                with get_db_connection() as conn:
                    c = conn.cursor()
                    if _is_master_role(role):
                        c.execute('SELECT name FROM masters WHERE id = ?', (user_id,))
                    else:
                        c.execute('SELECT name FROM managers WHERE id = ?', (user_id,))
                    r = c.fetchone()
                    if r:
                        employee_name = r[0]
            except Exception:
                pass
            role_label = 'мастер' if _is_master_role(role) else 'менеджер'
            employee_label = f"{employee_name} ({role_label})" if employee_name else f"{role_label} {user_id}"
            salary_payment_tag = f"salary_payment#{payment_id}"
            description_parts = [salary_payment_tag, category_name, f"сотруднику {employee_label}"]
            if period_start or period_end:
                description_parts.append(f"за период {period_start or '…'} — {period_end or '…'}")
            if comment:
                description_parts.append(comment)
            description = ". ".join(p for p in description_parts if p)

            pay_date = payment_date[:10] if payment_date else None
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT id FROM cash_transactions
                    WHERE transaction_type = 'expense' AND transaction_date = ? AND amount = ? AND description = ?
                    LIMIT 1
                    """,
                    (pay_date, amount, description),
                )
                existing = c.fetchone()
                if existing:
                    c.execute("UPDATE salary_payments SET cash_transaction_id = ? WHERE id = ?", (existing[0], payment_id))
                    conn.commit()
                    continue

            try:
                cash_transaction_id = FinanceService.create_transaction(
                    amount=amount,
                    transaction_type='expense',
                    category_name=category_name,
                    payment_method='cash',
                    description=description,
                    transaction_date=pay_date or payment_date,
                    payment_id=None,
                    created_by_id=created_by_id,
                    created_by_username=created_by_username,
                    skip_balance_check=True,
                )
                if cash_transaction_id:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("UPDATE salary_payments SET cash_transaction_id = ? WHERE id = ?", (cash_transaction_id, payment_id))
                        conn.commit()
                    created += 1
                    logger.info("Дозаполнена кассовая операция для выплаты зарплаты id=%s, cash_transaction_id=%s", payment_id, cash_transaction_id)
            except Exception as e:
                logger.warning("Не удалось создать кассовую операцию для salary_payment id=%s: %s", payment_id, e)
        return created

    @staticmethod
    @handle_service_error
    def get_cash_reconciliation(date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, float]:
        """
        Сверка зарплатного отчёта с кассой за период.

        Возвращает:
        - cash_income_total: приход по кассе (как в /finance/cash "Приход за период")
        - salary_revenue_total: выручка, учтенная в зарплатном модуле
        - diff: разница (cash - salary)
        """
        from app.services.finance_service import FinanceService

        cash_summary = FinanceService.get_cash_summary(date_from=date_from, date_to=date_to)
        salary_totals = SalaryDashboardService.get_salary_period_totals(date_from=date_from, date_to=date_to)

        cash_income_total = float((cash_summary or {}).get("total_income") or 0.0)
        salary_revenue_total = float((salary_totals or {}).get("total_revenue_cents") or 0) / 100.0
        return {
            "cash_income_total": cash_income_total,
            "salary_revenue_total": salary_revenue_total,
            "diff": cash_income_total - salary_revenue_total,
        }

    @staticmethod
    @handle_service_error
    def get_profit_details_by_orders(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Детализация выручки/прибыли по заявкам за период (по датам оплат).
        """
        rows: List[Dict[str, Any]] = []
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(payments)")
            pay_cols = [r[1] for r in cursor.fetchall()]
            kind_filter = " AND (p.kind IS NULL OR p.kind != 'refund')" if 'kind' in pay_cols else ""
            status_filter = " AND p.status = 'captured'" if 'status' in pay_cols else " AND (p.status IS NULL OR p.status != 'cancelled')"

            params: List[Any] = []
            date_filter = ""
            if date_from:
                date_filter += " AND DATE(COALESCE(p.payment_date, p.created_at)) >= DATE(?)"
                params.append(date_from)
            if date_to:
                date_filter += " AND DATE(COALESCE(p.payment_date, p.created_at)) <= DATE(?)"
                params.append(date_to)

            cursor.execute(
                f"""
                SELECT DISTINCT p.order_id
                FROM payments p
                WHERE p.order_id IS NOT NULL
                  AND (p.is_cancelled = 0 OR p.is_cancelled IS NULL)
                  {status_filter}
                  {kind_filter}
                  {date_filter}
                ORDER BY p.order_id DESC
                LIMIT ?
                """,
                params + [max(1, int(limit or 200))],
            )
            order_ids = [int(r[0]) for r in cursor.fetchall() if r and r[0]]
            if not order_ids:
                return rows

            placeholders = ",".join("?" for _ in order_ids)
            cursor.execute(
                f"""
                SELECT o.id, o.order_id, o.manager_id, o.master_id,
                       COALESCE(mgr.name, '—') AS manager_name,
                       COALESCE(ms.name, '—') AS master_name
                FROM orders o
                LEFT JOIN managers mgr ON mgr.id = o.manager_id
                LEFT JOIN masters ms ON ms.id = o.master_id
                WHERE o.id IN ({placeholders})
                """,
                order_ids,
            )
            meta_by_order = {int(r["id"]): dict(r) for r in cursor.fetchall()}

            # Суммы начислений зарплаты по заявке: отдельно мастер и менеджер
            cursor.execute(
                f"""
                SELECT sa.order_id,
                       COALESCE(SUM(CASE WHEN LOWER(COALESCE(sa.role, '')) LIKE 'master%' THEN sa.amount_cents ELSE 0 END), 0) AS master_salary_cents,
                       COALESCE(SUM(CASE WHEN LOWER(COALESCE(sa.role, '')) LIKE 'manager%' THEN sa.amount_cents ELSE 0 END), 0) AS manager_salary_cents
                FROM salary_accruals sa
                WHERE sa.order_id IN ({placeholders})
                GROUP BY sa.order_id
                """,
                order_ids,
            )
            salary_by_order = {int(r["order_id"]): dict(r) for r in cursor.fetchall()}

        for order_id in order_ids:
            try:
                p = SalaryService.calculate_order_profit(order_id)
                meta = meta_by_order.get(order_id, {})
                sal = salary_by_order.get(order_id, {})
                rows.append({
                    "order_id": order_id,
                    "order_uuid": meta.get("order_id") or "",
                    "order_display": f"#{order_id}",
                    "manager_name": meta.get("manager_name") or "—",
                    "master_name": meta.get("master_name") or "—",
                    "revenue_cents": int(p.get("total_payments_cents") or 0),
                    "profit_cents": int(p.get("profit_cents") or 0),
                    "cost_cents": int(p.get("total_cost_cents") or 0),
                    "master_salary_cents": int(sal.get("master_salary_cents") or 0),
                    "manager_salary_cents": int(sal.get("manager_salary_cents") or 0),
                })
            except Exception as e:
                logger.warning("Не удалось рассчитать детали прибыли по заявке %s: %s", order_id, e)
        return rows

    @staticmethod
    @handle_service_error
    def get_not_in_salary_items(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Платежи за период, которые попали в кассу, но не попали в salary-выручку.
        Причина: по заявке отсутствуют начисления salary_accruals.

        Учитываются возвраты (kind='refund') со знаком минус, как в calculate_order_profit,
        иначе после полного возврата заявка ошибочно попадала сюда как «предоплата».
        """
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()

            cursor.execute("PRAGMA table_info(payments)")
            pay_cols = [r[1] for r in cursor.fetchall()]
            has_kind = "kind" in pay_cols
            if has_kind:
                net_pay_sum = """
                    COALESCE(SUM(
                        CASE WHEN p.kind = 'refund' THEN -p.amount ELSE p.amount END
                    ), 0)
                """
            else:
                net_pay_sum = "COALESCE(SUM(p.amount), 0)"
            status_filter = " AND p.status = 'captured'" if 'status' in pay_cols else " AND (p.status IS NULL OR p.status != 'cancelled')"

            params: List[Any] = []
            date_filter = ""
            if date_from:
                date_filter += " AND DATE(COALESCE(p.payment_date, p.created_at)) >= DATE(?)"
                params.append(date_from)
            if date_to:
                date_filter += " AND DATE(COALESCE(p.payment_date, p.created_at)) <= DATE(?)"
                params.append(date_to)

            _net = net_pay_sum.strip()
            not_in_salary_sql = f"""
                SELECT p.order_id,
                       {_net} AS amount,
                       MIN(COALESCE(p.payment_date, p.created_at)) AS first_payment_date
                FROM payments p
                WHERE p.order_id IS NOT NULL
                  AND (p.is_cancelled = 0 OR p.is_cancelled IS NULL)
                  {status_filter}
                  {date_filter}
                GROUP BY p.order_id
                HAVING {_net} > 0
            """
            cursor.execute(not_in_salary_sql, params)
            payment_rows = [dict(r) for r in cursor.fetchall()]
            if not payment_rows:
                return []

            order_ids = [int(r["order_id"]) for r in payment_rows if r.get("order_id")]
            placeholders = ",".join("?" for _ in order_ids)

            cursor.execute(
                f"SELECT DISTINCT order_id FROM salary_accruals WHERE order_id IN ({placeholders}) AND order_id IS NOT NULL",
                order_ids,
            )
            order_ids_with_salary = {int(r[0]) for r in cursor.fetchall() if r and r[0]}

            cursor.execute(
                f"""
                SELECT o.id, o.order_id,
                       COALESCE(mgr.name, '—') AS manager_name,
                       COALESCE(ms.name, '—') AS master_name,
                       COALESCE(os.name, '—') AS status_name
                FROM orders o
                LEFT JOIN managers mgr ON mgr.id = o.manager_id
                LEFT JOIN masters ms ON ms.id = o.master_id
                LEFT JOIN order_statuses os ON os.id = o.status_id
                WHERE o.id IN ({placeholders})
                """,
                order_ids,
            )
            order_meta = {int(r["id"]): dict(r) for r in cursor.fetchall()}

            result: List[Dict[str, Any]] = []
            for pr in payment_rows:
                oid = int(pr.get("order_id") or 0)
                if oid <= 0 or oid in order_ids_with_salary:
                    continue
                meta = order_meta.get(oid, {})
                result.append({
                    "order_id": oid,
                    "order_uuid": meta.get("order_id") or "",
                    "order_display": f"#{oid}",
                    "payment_amount": float(pr.get("amount") or 0.0),
                    "payment_date": pr.get("first_payment_date"),
                    "manager_name": meta.get("manager_name") or "—",
                    "master_name": meta.get("master_name") or "—",
                    "status_name": meta.get("status_name") or "—",
                    "reason": "Предоплата по заявке (еще не попала в salary)",
                })
            return result
