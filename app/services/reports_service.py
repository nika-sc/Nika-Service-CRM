"""
Сервис для генерации отчетов.
"""
from typing import Dict, List, Optional, Any
from app.database.queries.warehouse_queries import WarehouseQueries
from app.database.queries.order_queries import OrderQueries
from app.database.queries.payment_queries import PaymentQueries
from app.services.finance_service import FinanceService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.error_handlers import handle_service_error
from app.utils.cache import cache_result
from app.database.connection import get_db_connection
import sqlite3
import logging
from datetime import datetime, timedelta
from app.utils.datetime_utils import get_moscow_now_str

logger = logging.getLogger(__name__)


class ReportsService:
    """Сервис для генерации отчетов."""
    
    @staticmethod
    @cache_result(timeout=120, key_prefix='reports_stock')
    @handle_service_error
    def get_stock_report(
        category: Optional[str] = None,
        low_stock_only: bool = False
    ) -> Dict[str, Any]:
        """
        Генерирует отчет по остаткам товаров.
        
        Args:
            category: Фильтр по категории
            low_stock_only: Только товары с низким остатком
            
        Returns:
            Словарь с данными отчета
        """
        result = WarehouseQueries.get_stock_levels(
            search_query=None,
            category=category,
            low_stock_only=low_stock_only,
            page=1,
            per_page=10000  # Получаем все товары для отчета
        )
        
        items = result['items']
        total_value = sum((item.get('retail_price') or 0) * (item.get('stock_quantity') or 0) for item in items)
        total_cost = sum((item.get('purchase_price') or 0) * (item.get('stock_quantity') or 0) for item in items)
        total_margin = total_value - total_cost
        
        return {
            'items': items,
            'total_items': len(items),
            'total_value': total_value,
            'total_cost': total_cost,
            'total_margin': total_margin,
            'low_stock_count': len([i for i in items if i.get('is_low_stock')])
        }
    
    @staticmethod
    @cache_result(timeout=120, key_prefix='reports_purchases')
    @handle_service_error
    def get_purchases_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        supplier_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Генерирует отчет по закупкам.
        
        Args:
            date_from: Дата начала
            date_to: Дата окончания
            supplier_id: Фильтр по поставщику
            
        Returns:
            Словарь с данными отчета
        """
        result = WarehouseQueries.get_purchases(
            supplier_id=supplier_id,
            status='completed',
            date_from=date_from,
            date_to=date_to,
            page=1,
            per_page=10000
        )
        
        purchases = result['items']
        total_amount = sum(p.get('total_amount', 0) for p in purchases)
        total_count = len(purchases)
        
        return {
            'purchases': purchases,
            'total_count': total_count,
            'total_amount': total_amount,
            'date_from': date_from,
            'date_to': date_to
        }
    
    @staticmethod
    @cache_result(timeout=180, key_prefix='reports_sales')
    @handle_service_error
    def get_sales_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        customer_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Генерирует отчет по продажам.
        
        Args:
            date_from: Дата начала
            date_to: Дата окончания
            customer_id: Фильтр по клиенту
            
        Returns:
            Словарь с данными отчета
        """
        # Используем оптимизированный SQL запрос с агрегацией вместо N+1
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Проверяем наличие колонок kind и status в payments
            cursor.execute("PRAGMA table_info(payments)")
            pay_cols = [r[1] for r in cursor.fetchall()]
            has_kind = "kind" in pay_cols
            has_status = "status" in pay_cols
            
            # Строим запрос для заявок с учетом фильтрации по дате
            where_clauses = ["(o.hidden = 0 OR o.hidden IS NULL)"]
            params = []
            
            if customer_id:
                where_clauses.append("o.customer_id = ?")
                params.append(customer_id)
            
            # Если указаны даты, фильтруем по дате создания заявки
            if date_from or date_to:
                # Если date_from == date_to, используем строгое равенство
                if date_from and date_to and date_from == date_to:
                    where_clauses.append("DATE(o.created_at) = DATE(?)")
                    params.append(date_from)
                else:
                    # Иначе используем диапазон
                    if date_from:
                        where_clauses.append("DATE(o.created_at) >= DATE(?)")
                        params.append(date_from)
                    if date_to:
                        where_clauses.append("DATE(o.created_at) <= DATE(?)")
                        params.append(date_to)
            
            where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            
            # Оптимизированный запрос: получаем все данные одним запросом с агрегацией
            # Считаем оплаты с учетом kind и status
            payment_sum_sql = """
                COALESCE((
                    SELECT SUM(
                        CASE 
                            WHEN kind = 'refund' THEN -amount 
                            ELSE amount 
                        END
                    )
                    FROM payments p
                    WHERE p.order_id = o.id
                      AND (p.is_cancelled = 0 OR p.is_cancelled IS NULL)
            """
            if has_status:
                payment_sum_sql += " AND p.status = 'captured'"
            payment_sum_sql += "), 0)"
            
            if not has_kind:
                # Старая схема без kind
                payment_sum_sql = """
                    COALESCE((
                        SELECT SUM(amount)
                        FROM payments p
                        WHERE p.order_id = o.id
                          AND (p.is_cancelled = 0 OR p.is_cancelled IS NULL)
                """
                if has_status:
                    payment_sum_sql += " AND p.status = 'captured'"
                payment_sum_sql += "), 0)"
            
            # Получаем заявки с агрегированными суммами одним запросом.
            # Важно: избегаем коррелированных подзапросов на order_services/order_parts/payments
            # (они выполняются "на каждую строку") и вместо этого используем предагрегацию (derived tables) + JOIN.
            if has_kind:
                paid_expr = "SUM(CASE WHEN p.kind = 'refund' THEN -p.amount ELSE p.amount END)"
            else:
                paid_expr = "SUM(p.amount)"

            paid_where = ["(p.is_cancelled = 0 OR p.is_cancelled IS NULL)"]
            if has_status:
                paid_where.append("p.status = 'captured'")
            paid_where_sql = " AND ".join(paid_where)

            payments_agg_sql = f"""
                SELECT
                    p.order_id,
                    COALESCE({paid_expr}, 0) AS paid
                FROM payments p
                WHERE {paid_where_sql}
                GROUP BY p.order_id
            """

            cursor.execute(f'''
                SELECT 
                    o.id,
                    o.order_id,
                    o.created_at,
                    o.customer_id,
                    c.name AS client_name,
                    c.phone,
                    c.email,
                    COALESCE(osum.services_total, 0) AS services_total,
                    COALESCE(psum.parts_total, 0) AS parts_total,
                    COALESCE(pay.paid, 0) AS paid,
                    (SELECT id FROM payments 
                     WHERE order_id = o.id 
                     ORDER BY payment_date DESC, created_at DESC 
                     LIMIT 1) AS payment_id
                FROM orders o
                LEFT JOIN customers c ON c.id = o.customer_id
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
                {where_sql}
                  AND (COALESCE(osum.services_total, 0) > 0 OR COALESCE(psum.parts_total, 0) > 0)
                ORDER BY o.created_at DESC
            ''', params)
            
            orders_with_sales = []
            total_services = 0.0
            total_parts = 0.0
            total_payments = 0.0
            
            for row in cursor.fetchall():
                order = dict(row)
                services_total = float(order.get('services_total', 0) or 0)
                parts_total = float(order.get('parts_total', 0) or 0)
                paid = float(order.get('paid', 0) or 0)
                
                # Обогащаем строки для шаблона
                order['services_total'] = services_total
                order['parts_total'] = parts_total
                order['total_revenue'] = services_total + parts_total
                order['paid'] = paid
                order['debt'] = (services_total + parts_total) - paid
                order['sale_type'] = 'order'  # Тип продажи: из заявки
                
                orders_with_sales.append(order)
                
                total_services += services_total
                total_parts += parts_total
                total_payments += paid
        
        # Получаем продажи из магазина
        shop_sales_params = []
        shop_sales_where = []
        
        # Если date_from == date_to, используем строгое равенство
        if date_from and date_to and date_from == date_to:
            shop_sales_where.append("DATE(ss.sale_date) = DATE(?)")
            shop_sales_params.append(date_from)
        else:
            # Иначе используем диапазон
            if date_from:
                shop_sales_where.append("DATE(ss.sale_date) >= DATE(?)")
                shop_sales_params.append(date_from)
            if date_to:
                shop_sales_where.append("DATE(ss.sale_date) <= DATE(?)")
                shop_sales_params.append(date_to)
        if customer_id:
            shop_sales_where.append("ss.customer_id = ?")
            shop_sales_params.append(customer_id)
        
        shop_sales_where_sql = " AND " + " AND ".join(shop_sales_where) if shop_sales_where else ""
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем продажи из магазина
            cursor.execute(f'''
                SELECT 
                    ss.id,
                    ss.sale_date AS created_at,
                    ss.customer_id,
                    COALESCE(c.name, ss.customer_name) AS client_name,
                    ss.final_amount AS total_revenue,
                    ss.paid_amount AS paid,
                    ss.final_amount - ss.paid_amount AS debt,
                    (SELECT COALESCE(SUM(CASE WHEN item_type = 'service' THEN price * quantity ELSE 0 END), 0) 
                     FROM shop_sale_items WHERE shop_sale_id = ss.id) AS services_total,
                    (SELECT COALESCE(SUM(CASE WHEN item_type = 'part' THEN price * quantity ELSE 0 END), 0) 
                     FROM shop_sale_items WHERE shop_sale_id = ss.id) AS parts_total,
                    NULL AS order_id,
                    NULL AS order_uuid,
                    'shop' AS sale_type
                FROM shop_sales AS ss
                LEFT JOIN customers c ON c.id = ss.customer_id
                WHERE 1=1 {shop_sales_where_sql}
                ORDER BY ss.sale_date DESC, ss.created_at DESC
            ''', shop_sales_params)
            
            shop_sales = [dict(r) for r in cursor.fetchall()]
            
            # Добавляем продажи из магазина к заявкам
            for shop_sale in shop_sales:
                orders_with_sales.append(shop_sale)
                total_services += shop_sale.get('services_total', 0)
                total_parts += shop_sale.get('parts_total', 0)
                total_payments += shop_sale.get('paid', 0)
        
        # Сортируем все продажи по дате
        orders_with_sales.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        total_revenue = total_services + total_parts
        total_debt = total_revenue - total_payments
        
        return {
            'orders': orders_with_sales,
            'total_orders': len(orders_with_sales),
            'total_services': total_services,
            'total_parts': total_parts,
            'total_payments': total_payments,
            'total_revenue': total_revenue,
            'total_debt': total_debt,
            'date_from': date_from,
            'date_to': date_to
        }
    
    @staticmethod
    @cache_result(timeout=180, key_prefix='reports_profitability')
    @handle_service_error
    def get_profitability_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Генерирует отчет по маржинальности.
        Учитывает продажи из заявок (order_parts) и из магазина (shop_sale_items).
        
        Args:
            date_from: Дата начала
            date_to: Дата окончания
            
        Returns:
            Словарь с данными отчета
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Объединяем продажи из заявок и из магазина
                # Используем UNION ALL для объединения данных
                
                # 1. Продажи из заявок (order_parts)
                where_clauses_order = ["(o.hidden = 0 OR o.hidden IS NULL)", "p.is_deleted = 0"]
                params_order = []
                
                if date_from:
                    where_clauses_order.append('DATE(op.created_at) >= DATE(?)')
                    params_order.append(date_from)
                
                if date_to:
                    where_clauses_order.append('DATE(op.created_at) <= DATE(?)')
                    params_order.append(date_to)
                
                where_sql_order = 'WHERE ' + ' AND '.join(where_clauses_order)
                
                query_order = f'''
                    SELECT 
                        p.id AS part_id,
                        p.name AS part_name,
                        p.part_number,
                        COALESCE(pc.name, p.category) AS category,
                        SUM(op.quantity) AS total_sold,
                        SUM(op.quantity * op.price) AS total_revenue,
                        AVG(COALESCE(op.purchase_price, p.purchase_price, 0)) AS avg_purchase_price,
                        AVG(op.price) AS avg_retail_price
                    FROM order_parts AS op
                    JOIN orders AS o ON o.id = op.order_id
                    JOIN parts AS p ON p.id = op.part_id
                    LEFT JOIN part_categories AS pc ON pc.id = p.category_id
                    {where_sql_order}
                    GROUP BY p.id, p.name, p.part_number, COALESCE(pc.name, p.category)
                    HAVING SUM(op.quantity) > 0
                '''
                
                # 2. Продажи из магазина (shop_sale_items)
                where_clauses_shop = ["ssi.item_type = 'part'", "p.is_deleted = 0"]
                params_shop = []
                
                if date_from:
                    where_clauses_shop.append('DATE(ss.created_at) >= DATE(?)')
                    params_shop.append(date_from)
                
                if date_to:
                    where_clauses_shop.append('DATE(ss.created_at) <= DATE(?)')
                    params_shop.append(date_to)
                
                where_sql_shop = 'WHERE ' + ' AND '.join(where_clauses_shop)
                
                query_shop = f'''
                    SELECT 
                        p.id AS part_id,
                        p.name AS part_name,
                        p.part_number,
                        COALESCE(pc.name, p.category) AS category,
                        SUM(ssi.quantity) AS total_sold,
                        SUM(ssi.quantity * ssi.price) AS total_revenue,
                        AVG(COALESCE(ssi.purchase_price, p.purchase_price, 0)) AS avg_purchase_price,
                        AVG(ssi.price) AS avg_retail_price
                    FROM shop_sale_items AS ssi
                    JOIN shop_sales AS ss ON ss.id = ssi.shop_sale_id
                    JOIN parts AS p ON p.id = ssi.part_id
                    LEFT JOIN part_categories AS pc ON pc.id = p.category_id
                    {where_sql_shop}
                    GROUP BY p.id, p.name, p.part_number, COALESCE(pc.name, p.category)
                    HAVING SUM(ssi.quantity) > 0
                '''
                
                # Объединяем результаты
                combined_query = f'''
                    SELECT 
                        part_id,
                        part_name,
                        part_number,
                        category,
                        SUM(total_sold) AS total_sold,
                        SUM(total_revenue) AS total_revenue,
                        AVG(avg_purchase_price) AS avg_purchase_price,
                        AVG(avg_retail_price) AS avg_retail_price
                    FROM (
                        {query_order}
                        UNION ALL
                        {query_shop}
                    )
                    GROUP BY part_id, part_name, part_number, category
                    HAVING SUM(total_sold) > 0
                    ORDER BY total_revenue DESC
                '''
                
                # Объединяем параметры
                all_params = params_order + params_shop
                
                cursor.execute(combined_query, all_params)
                rows = cursor.fetchall()
                
                items = []
                total_revenue = 0.0
                total_cost = 0.0
                
                for row in rows:
                    item = dict(row)
                    total_sold = float(item.get('total_sold', 0) or 0)
                    avg_purchase = float(item.get('avg_purchase_price', 0) or 0)
                    avg_retail = float(item.get('avg_retail_price', 0) or 0)
                    
                    revenue = float(item.get('total_revenue', 0) or 0)
                    cost = total_sold * avg_purchase
                    margin = revenue - cost
                    margin_percent = (margin / revenue * 100) if revenue > 0 else 0
                    
                    item['total_cost'] = cost
                    item['margin'] = margin
                    item['margin_percent'] = margin_percent
                    
                    items.append(item)
                    total_revenue += revenue
                    total_cost += cost
                
                total_margin = total_revenue - total_cost
                total_margin_percent = (total_margin / total_revenue * 100) if total_revenue > 0 else 0

                # Выручка по услугам (заявки + магазин)
                services_revenue = 0.0
                try:
                    svc_params = []
                    svc_where_order = []
                    svc_where_shop = []
                    if date_from:
                        svc_where_order.append('DATE(o.created_at) >= DATE(?)')
                        svc_where_shop.append('DATE(ss.created_at) >= DATE(?)')
                        svc_params.append(date_from)
                    if date_to:
                        svc_where_order.append('DATE(o.created_at) <= DATE(?)')
                        svc_where_shop.append('DATE(ss.created_at) <= DATE(?)')
                        svc_params.append(date_to)
                    svc_where_order_sql = ' AND ' + ' AND '.join(svc_where_order) if svc_where_order else ''
                    svc_where_shop_sql = ' AND ' + ' AND '.join(svc_where_shop) if svc_where_shop else ''
                    
                    cursor.execute(f'''
                        SELECT COALESCE(SUM(os.price * os.quantity), 0) AS total
                        FROM order_services os
                        JOIN orders o ON o.id = os.order_id
                        WHERE (o.hidden = 0 OR o.hidden IS NULL){svc_where_order_sql}
                    ''', svc_params)
                    order_services_total = cursor.fetchone()['total'] or 0
                    
                    cursor.execute(f'''
                        SELECT COALESCE(SUM(ssi.price * ssi.quantity), 0) AS total
                        FROM shop_sale_items ssi
                        JOIN shop_sales ss ON ss.id = ssi.shop_sale_id
                        WHERE ssi.item_type = 'service'{svc_where_shop_sql}
                    ''', svc_params)
                    shop_services_total = cursor.fetchone()['total'] or 0
                    
                    services_revenue = float(order_services_total) + float(shop_services_total)
                except Exception as e:
                    logger.warning(f"Не удалось посчитать выручку по услугам: {e}")
                
                total_revenue_all = total_revenue + services_revenue
                
                return {
                    'items': items,
                    'total_revenue': total_revenue,
                    'total_cost': total_cost,
                    'total_margin': total_margin,
                    'total_margin_percent': total_margin_percent,
                    'services_revenue': services_revenue,
                    'total_revenue_all': total_revenue_all,
                    'date_from': date_from,
                    'date_to': date_to
                }
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета по маржинальности: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при генерации отчета: {e}")
    
    @staticmethod
    @handle_service_error
    def get_customer_statistics_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Генерирует отчет по статистике клиентов.
        
        Args:
            date_from: Дата начала
            date_to: Дата окончания
            
        Returns:
            Список клиентов со статистикой
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                where_clauses = ["(o.hidden = 0 OR o.hidden IS NULL)"]
                params: List[Any] = []

                if date_from:
                    where_clauses.append("DATE(o.created_at) >= DATE(?)")
                    params.append(date_from)
                if date_to:
                    where_clauses.append("DATE(o.created_at) <= DATE(?)")
                    params.append(date_to)

                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

                # Считаем сумму по заявке как (услуги + товары) из order_services и order_parts.
                # Важно: раньше total_spent учитывал только услуги, из-за чего суммы по клиентам были занижены.
                cursor.execute(f"""
                    SELECT
                        c.id,
                        c.name,
                        c.phone,
                        c.email,
                        COUNT(DISTINCT o.id) AS orders_count,
                        COALESCE(SUM(ot.total), 0) AS total_spent,
                        COALESCE(AVG(ot.total), 0) AS avg_order_value,
                        MAX(o.created_at) AS last_order_date
                    FROM customers c
                    JOIN orders o ON o.customer_id = c.id
                    LEFT JOIN (
                        SELECT
                            o2.id AS order_id,
                            COALESCE(osum.services_total, 0) + COALESCE(psum.parts_total, 0) AS total
                        FROM orders o2
                        LEFT JOIN (
                            SELECT order_id, SUM(price * quantity) AS services_total
                            FROM order_services
                            GROUP BY order_id
                        ) osum ON osum.order_id = o2.id
                        LEFT JOIN (
                            SELECT order_id, SUM(price * quantity) AS parts_total
                            FROM order_parts
                            GROUP BY order_id
                        ) psum ON psum.order_id = o2.id
                    ) ot ON ot.order_id = o.id
                    {where_sql}
                    GROUP BY c.id
                    HAVING COUNT(DISTINCT o.id) > 0
                    ORDER BY total_spent DESC
                """, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета по клиентам: {e}")
            raise DatabaseError(f"Ошибка при генерации отчета: {e}")

    @staticmethod
    @cache_result(timeout=120, key_prefix='reports_cash')
    @handle_service_error
    def get_cash_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Касса: отчет по поступлениям (оплатам и операциям) за период.
        Объединяет данные из payments (оплаты по заявкам) и cash_transactions (доходы/расходы).

        По умолчанию показывает "сегодня".
        """
        if not date_from and not date_to:
            today = get_moscow_now_str('%Y-%m-%d')
            date_from = today
            date_to = today

        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()

                # Параметры для фильтрации по датам
                where_clauses_payments = []
                where_clauses_transactions = []
                params_payments: List[Any] = []
                params_transactions: List[Any] = []

                if date_from:
                    where_clauses_payments.append("DATE(p.payment_date) >= DATE(?)")
                    params_payments.append(date_from)
                    where_clauses_transactions.append("DATE(ct.transaction_date) >= DATE(?)")
                    params_transactions.append(date_from)
                if date_to:
                    where_clauses_payments.append("DATE(p.payment_date) <= DATE(?)")
                    params_payments.append(date_to)
                    where_clauses_transactions.append("DATE(ct.transaction_date) <= DATE(?)")
                    params_transactions.append(date_to)

                where_sql_payments = ("WHERE " + " AND ".join(where_clauses_payments)) if where_clauses_payments else ""
                where_sql_transactions = ("WHERE " + " AND ".join(where_clauses_transactions)) if where_clauses_transactions else ""

                # 1. Оплаты из payments (по заявкам)
                cursor.execute(f'''
                    SELECT
                        p.payment_type,
                        COUNT(*) AS payments_count,
                        COALESCE(SUM(p.amount), 0) AS total_amount
                    FROM payments AS p
                    {where_sql_payments}
                    GROUP BY p.payment_type
                ''', params_payments)
                payments_by_type = [dict(r) for r in cursor.fetchall()]

                # 2. Операции из cash_transactions (доходы и расходы)
                if where_sql_transactions:
                    where_sql_transactions_income = where_sql_transactions + " AND ct.transaction_type = 'income'"
                else:
                    where_sql_transactions_income = "WHERE ct.transaction_type = 'income'"
                
                cursor.execute(f'''
                    SELECT
                        ct.payment_method AS payment_type,
                        COUNT(*) AS payments_count,
                        COALESCE(SUM(ct.amount), 0) AS total_amount
                    FROM cash_transactions AS ct
                    {where_sql_transactions_income}
                    GROUP BY ct.payment_method
                ''', params_transactions)
                transactions_by_type = [dict(r) for r in cursor.fetchall()]

                # Сводка по типам оплат из cash_transactions (оплаты из payments уже включены)
                by_type_dict = {}
                for row in transactions_by_type:
                    payment_type = row['payment_type'] or 'cash'
                    if payment_type not in by_type_dict:
                        by_type_dict[payment_type] = {'payment_type': payment_type, 'payments_count': 0, 'total_amount': 0.0}
                    by_type_dict[payment_type]['payments_count'] += row['payments_count']
                    by_type_dict[payment_type]['total_amount'] += row['total_amount']
                
                by_type = sorted(by_type_dict.values(), key=lambda x: x['total_amount'], reverse=True)

                # Общая сумма из cash_transactions (только доходы)
                # Оплаты из payments уже включены в cash_transactions, поэтому считаем только их
                cursor.execute(f'''
                    SELECT
                        COUNT(*) AS total_payments,
                        COALESCE(SUM(ct.amount), 0) AS total_amount
                    FROM cash_transactions AS ct
                    {where_sql_transactions_income}
                ''', params_transactions)
                transactions_totals_row = cursor.fetchone()
                total_payments = int(transactions_totals_row['total_payments'] or 0) if transactions_totals_row else 0
                total_amount = float(transactions_totals_row['total_amount'] or 0) if transactions_totals_row else 0.0

                # Детализация: показываем только кассовые операции из cash_transactions
                # (оплаты из payments уже включены в cash_transactions автоматически через PaymentService.add_payment)
                # Это исключает дублирование операций
                # Также получаем информацию о выплатах зарплаты для ссылок на личные кабинеты
                cursor.execute(f'''
                    SELECT
                        ct.id,
                        ct.order_id,
                        o.order_id AS order_uuid,
                        o.id AS order_internal_id,
                        o.customer_id,
                        c.name AS client_name,
                        ct.amount,
                        ct.payment_method AS payment_type,
                        ct.transaction_date,
                        ct.created_by_username,
                        ct.description,
                        'transaction' AS source_type,
                        tc.name AS category_name,
                        ct.shop_sale_id,
                        ct.payment_id,
                        -- Информация о выплате зарплаты (если есть)
                        sp.user_id AS salary_employee_id,
                        sp.role AS salary_employee_role,
                        CASE 
                            WHEN sp.role = 'master' THEN m.name
                            WHEN sp.role = 'manager' THEN mg.name
                            ELSE NULL
                        END AS salary_employee_name
                    FROM cash_transactions AS ct
                    LEFT JOIN orders AS o ON o.id = ct.order_id
                    LEFT JOIN customers AS c ON c.id = o.customer_id
                    LEFT JOIN transaction_categories AS tc ON tc.id = ct.category_id
                    LEFT JOIN salary_payments AS sp ON sp.cash_transaction_id = ct.id
                    LEFT JOIN masters AS m ON m.id = sp.user_id AND sp.role = 'master'
                    LEFT JOIN managers AS mg ON mg.id = sp.user_id AND sp.role = 'manager'
                    {where_sql_transactions_income}
                    ORDER BY ct.transaction_date DESC, ct.id DESC
                    LIMIT 500
                ''', params_transactions)
                payments = [dict(r) for r in cursor.fetchall()]

                return {
                    'date_from': date_from,
                    'date_to': date_to,
                    'total_payments': total_payments,
                    'total_amount': total_amount,
                    'by_type': by_type,
                    'payments': payments,
                }
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета 'Касса': {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при генерации отчета: {e}")

    @staticmethod
    @cache_result(timeout=120, key_prefix='reports_categories')
    @handle_service_error
    def get_categories_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        category_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отчет по статьям доходов и расходов за период.
        
        Args:
            date_from: Дата начала
            date_to: Дата окончания
            category_type: Тип категории ('income' или 'expense')
            
        Returns:
            Словарь с данными отчета
        """
        if not date_from and not date_to:
            today = get_moscow_now_str('%Y-%m-%d')
            date_from = today
            date_to = today

        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()

                # Параметры для фильтрации
                where_clauses = []
                params: List[Any] = []

                if date_from:
                    where_clauses.append("DATE(ct.transaction_date) >= DATE(?)")
                    params.append(date_from)
                if date_to:
                    where_clauses.append("DATE(ct.transaction_date) <= DATE(?)")
                    params.append(date_to)
                if category_type:
                    where_clauses.append("ct.transaction_type = ?")
                    params.append(category_type)

                where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

                # Получаем статистику по категориям
                cursor.execute(f'''
                    SELECT
                        tc.id AS category_id,
                        tc.name AS category_name,
                        tc.type AS category_type,
                        tc.color AS category_color,
                        COUNT(*) AS transactions_count,
                        COALESCE(SUM(ct.amount), 0) AS total_amount,
                        COALESCE(AVG(ct.amount), 0) AS avg_amount,
                        COALESCE(MAX(ct.amount), 0) AS max_amount,
                        COALESCE(MIN(ct.amount), 0) AS min_amount
                    FROM cash_transactions AS ct
                    JOIN transaction_categories AS tc ON tc.id = ct.category_id
                    {where_sql}
                    GROUP BY tc.id, tc.name, tc.type, tc.color
                    ORDER BY tc.type DESC, total_amount DESC
                ''', params)
                categories_stats = [dict(r) for r in cursor.fetchall()]

                # Общая статистика
                cursor.execute(f'''
                    SELECT
                        ct.transaction_type,
                        COUNT(*) AS transactions_count,
                        COALESCE(SUM(ct.amount), 0) AS total_amount
                    FROM cash_transactions AS ct
                    {where_sql}
                    GROUP BY ct.transaction_type
                ''', params)
                totals_by_type = [dict(r) for r in cursor.fetchall()]

                # Общая сумма
                cursor.execute(f'''
                    SELECT
                        COUNT(*) AS total_transactions,
                        COALESCE(SUM(CASE WHEN ct.transaction_type = 'income' THEN ct.amount ELSE 0 END), 0) AS total_income,
                        COALESCE(SUM(CASE WHEN ct.transaction_type = 'expense' THEN ct.amount ELSE 0 END), 0) AS total_expense
                    FROM cash_transactions AS ct
                    {where_sql}
                ''', params)
                totals_row = cursor.fetchone()
                total_transactions = int(totals_row['total_transactions'] or 0) if totals_row else 0
                total_income = float(totals_row['total_income'] or 0) if totals_row else 0.0
                total_expense = float(totals_row['total_expense'] or 0) if totals_row else 0.0
                total_balance = total_income - total_expense

                # Детализация по категориям (топ-200)
                cursor.execute(f'''
                    SELECT
                        ct.id,
                        ct.transaction_date,
                        ct.transaction_type,
                        ct.amount,
                        ct.payment_method,
                        ct.description,
                        ct.created_by_username,
                        tc.name AS category_name,
                        tc.color AS category_color,
                        o.id AS order_internal_id,
                        o.order_id AS order_uuid,
                        c.id AS customer_id,
                        c.name AS client_name
                    FROM cash_transactions AS ct
                    JOIN transaction_categories AS tc ON tc.id = ct.category_id
                    LEFT JOIN orders AS o ON o.id = ct.order_id
                    LEFT JOIN customers AS c ON c.id = o.customer_id
                    {where_sql}
                    ORDER BY ct.transaction_date DESC, ct.created_at DESC
                    LIMIT 200
                ''', params)
                transactions = [dict(r) for r in cursor.fetchall()]

                return {
                    'date_from': date_from,
                    'date_to': date_to,
                    'category_type': category_type,
                    'categories_stats': categories_stats,
                    'totals_by_type': totals_by_type,
                    'total_transactions': total_transactions,
                    'total_income': total_income,
                    'total_expense': total_expense,
                    'total_balance': total_balance,
                    'transactions': transactions
                }
        except Exception as e:
            logger.error(f"Ошибка при генерации отчета 'Статьи доходов и расходов': {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при генерации отчета: {e}")

    @staticmethod
    @cache_result(timeout=120, key_prefix='reports_summary')
    def get_summary_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Генерирует сводный отчёт с общей статистикой.
        
        Args:
            date_from: Начало периода (YYYY-MM-DD)
            date_to: Конец периода (YYYY-MM-DD)
            
        Returns:
            Словарь со сводными данными
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Формируем условия даты
                date_conditions = []
                params = []
                if date_from:
                    date_conditions.append("DATE(created_at) >= DATE(?)")
                    params.append(date_from)
                if date_to:
                    date_conditions.append("DATE(created_at) <= DATE(?)")
                    params.append(date_to)
                
                date_where = " AND ".join(date_conditions) if date_conditions else "1=1"
                today_moscow = get_moscow_now_str('%Y-%m-%d')
                
                # Статистика по заявкам
                # Если период не указан, показываем за сегодня
                if not date_from and not date_to:
                    date_where = "DATE(created_at) = DATE(?)"
                    params = [today_moscow]
                
                cursor.execute(f'''
                    SELECT 
                        COUNT(*) as total_orders,
                        COUNT(CASE WHEN DATE(created_at) = DATE(?) THEN 1 END) as today_orders
                    FROM orders
                    WHERE {date_where} AND (hidden = 0 OR hidden IS NULL)
                ''', [today_moscow] + params)
                orders_row = cursor.fetchone()
                orders_stats = {
                    'total': orders_row['total_orders'] if orders_row else 0,
                    'today': orders_row['today_orders'] if orders_row else 0
                }
                
                # Статистика по заявкам по статусам
                cursor.execute(f'''
                    SELECT 
                        s.name as status_name,
                        s.color as status_color,
                        COUNT(o.id) as count
                    FROM orders o
                    LEFT JOIN order_statuses s ON s.id = o.status_id
                    WHERE {date_where.replace('created_at', 'o.created_at')} AND (o.hidden = 0 OR o.hidden IS NULL)
                    GROUP BY o.status_id, s.name, s.color
                    ORDER BY count DESC
                ''', params)
                orders_by_status = [dict(r) for r in cursor.fetchall()]
                
                # Статистика по оплатам (приход денег) - объединяем оплаты из заявок и магазина
                payment_params = []
                
                # Формируем условия для фильтрации по датам
                # Если период не указан, показываем за сегодня
                if not date_from and not date_to:
                    today = get_moscow_now_str('%Y-%m-%d')
                    # Используем одинаковые условия для обоих источников
                    payment_date_condition = f"DATE(?)"
                    payment_params = [today, today]  # Один для payments, один для shop_sales
                else:
                    # Используем параметризованные запросы с одинаковыми параметрами
                    if date_from and date_to:
                        payment_date_condition = ">= DATE(?) AND <= DATE(?)"
                        payment_params = [date_from, date_to, date_from, date_to]  # Для payments и shop_sales
                    elif date_from:
                        payment_date_condition = ">= DATE(?)"
                        payment_params = [date_from, date_from]  # Для payments и shop_sales
                    elif date_to:
                        payment_date_condition = "<= DATE(?)"
                        payment_params = [date_to, date_to]  # Для payments и shop_sales
                    else:
                        payment_date_condition = "1=1"
                        payment_params = []
                
                # Объединяем оплаты из заявок и магазина
                if not date_from and not date_to:
                    # Случай "за сегодня" - используем прямое сравнение
                    cursor.execute(f'''
                        SELECT 
                            COALESCE(SUM(total_amount), 0) as total_income,
                            COUNT(*) as payments_count
                        FROM (
                            -- Оплаты из заявок
                            SELECT 
                                p.amount as total_amount
                            FROM payments p
                            JOIN orders o ON o.id = p.order_id
                            WHERE DATE(p.payment_date) = DATE(?) AND (o.hidden = 0 OR o.hidden IS NULL)
                            
                            UNION ALL
                            
                            -- Оплаты из магазина (только если paid_amount > 0)
                            SELECT 
                                ss.paid_amount as total_amount
                            FROM shop_sales ss
                            WHERE DATE(COALESCE(ss.sale_date, ss.created_at)) = DATE(?) AND ss.paid_amount > 0
                        ) combined_payments
                    ''', payment_params)
                else:
                    # Случай с периодом - используем параметризованные запросы
                    if date_from and date_to:
                        cursor.execute(f'''
                            SELECT 
                                COALESCE(SUM(total_amount), 0) as total_income,
                                COUNT(*) as payments_count
                            FROM (
                                -- Оплаты из заявок
                                SELECT 
                                    p.amount as total_amount
                                FROM payments p
                                JOIN orders o ON o.id = p.order_id
                                WHERE DATE(p.payment_date) >= DATE(?) AND DATE(p.payment_date) <= DATE(?) AND (o.hidden = 0 OR o.hidden IS NULL)
                                
                                UNION ALL
                                
                                -- Оплаты из магазина (только если paid_amount > 0)
                                SELECT 
                                    ss.paid_amount as total_amount
                                FROM shop_sales ss
                                WHERE DATE(COALESCE(ss.sale_date, ss.created_at)) >= DATE(?) AND DATE(COALESCE(ss.sale_date, ss.created_at)) <= DATE(?) AND ss.paid_amount > 0
                            ) combined_payments
                        ''', payment_params)
                    elif date_from:
                        cursor.execute(f'''
                            SELECT 
                                COALESCE(SUM(total_amount), 0) as total_income,
                                COUNT(*) as payments_count
                            FROM (
                                -- Оплаты из заявок
                                SELECT 
                                    p.amount as total_amount
                                FROM payments p
                                JOIN orders o ON o.id = p.order_id
                                WHERE DATE(p.payment_date) >= DATE(?) AND (o.hidden = 0 OR o.hidden IS NULL)
                                
                                UNION ALL
                                
                                -- Оплаты из магазина (только если paid_amount > 0)
                                SELECT 
                                    ss.paid_amount as total_amount
                                FROM shop_sales ss
                                WHERE DATE(COALESCE(ss.sale_date, ss.created_at)) >= DATE(?) AND ss.paid_amount > 0
                            ) combined_payments
                        ''', payment_params)
                    elif date_to:
                        cursor.execute(f'''
                            SELECT 
                                COALESCE(SUM(total_amount), 0) as total_income,
                                COUNT(*) as payments_count
                            FROM (
                                -- Оплаты из заявок
                                SELECT 
                                    p.amount as total_amount
                                FROM payments p
                                JOIN orders o ON o.id = p.order_id
                                WHERE DATE(p.payment_date) <= DATE(?) AND (o.hidden = 0 OR o.hidden IS NULL)
                                
                                UNION ALL
                                
                                -- Оплаты из магазина (только если paid_amount > 0)
                                SELECT 
                                    ss.paid_amount as total_amount
                                FROM shop_sales ss
                                WHERE DATE(COALESCE(ss.sale_date, ss.created_at)) <= DATE(?) AND ss.paid_amount > 0
                            ) combined_payments
                        ''', payment_params)
                    else:
                        cursor.execute(f'''
                            SELECT 
                                COALESCE(SUM(total_amount), 0) as total_income,
                                COUNT(*) as payments_count
                            FROM (
                                -- Оплаты из заявок
                                SELECT 
                                    p.amount as total_amount
                                FROM payments p
                                JOIN orders o ON o.id = p.order_id
                                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                                
                                UNION ALL
                                
                                -- Оплаты из магазина (только если paid_amount > 0)
                                SELECT 
                                    ss.paid_amount as total_amount
                                FROM shop_sales ss
                                WHERE ss.paid_amount > 0
                            ) combined_payments
                        ''', payment_params)
                payments_row = cursor.fetchone()
                income_stats = {
                    'total': float(payments_row['total_income']) if payments_row else 0,
                    'count': payments_row['payments_count'] if payments_row else 0
                }
                
                # Статистика по складу (поступления и списания)
                movement_params = []
                movement_conditions = []
                if date_from:
                    movement_conditions.append("DATE(created_at) >= DATE(?)")
                    movement_params.append(date_from)
                if date_to:
                    movement_conditions.append("DATE(created_at) <= DATE(?)")
                    movement_params.append(date_to)
                # Если период не указан, показываем за сегодня
                if not date_from and not date_to:
                    movement_where = "DATE(created_at) = DATE(?)"
                    movement_params = [today_moscow]
                else:
                    movement_where = " AND ".join(movement_conditions) if movement_conditions else "1=1"
                
                cursor.execute(f'''
                    SELECT 
                        movement_type,
                        COUNT(*) as count,
                        COALESCE(SUM(ABS(quantity)), 0) as total_qty
                    FROM stock_movements
                    WHERE {movement_where}
                    GROUP BY movement_type
                ''', movement_params)
                movements = {r['movement_type']: {'count': r['count'], 'qty': int(r['total_qty'])} 
                            for r in cursor.fetchall()}
                
                warehouse_stats = {
                    'in': max(0, int(movements.get('income', {}).get('qty', 0) or movements.get('purchase', {}).get('qty', 0) or 0)),
                    'out': max(0, int(movements.get('expense', {}).get('qty', 0) or 0)),
                    'sale': max(0, int(movements.get('sale', {}).get('qty', 0) or 0)),
                    'return': max(0, int(movements.get('return', {}).get('qty', 0) or 0))
                }
                
                # Последние заявки
                cursor.execute(f'''
                    SELECT o.id, o.order_id, c.name as client_name, 
                           s.name as status_name, s.color as status_color,
                           o.created_at
                    FROM orders o
                    LEFT JOIN customers c ON c.id = o.customer_id
                    LEFT JOIN order_statuses s ON s.id = o.status_id
                    WHERE {date_where.replace('created_at', 'o.created_at')} AND (o.hidden = 0 OR o.hidden IS NULL)
                    ORDER BY o.created_at DESC
                    LIMIT 10
                ''', params)
                recent_orders = [dict(r) for r in cursor.fetchall()]
                
                # Последние платежи - объединяем из заявок и магазина
                if not date_from and not date_to:
                    # Оплаты из заявок
                    cursor.execute(f'''
                        SELECT p.id, p.amount, p.payment_type, p.payment_date,
                               o.order_id, c.name as client_name,
                               'order' as payment_source
                        FROM payments p
                        JOIN orders o ON o.id = p.order_id
                        LEFT JOIN customers c ON c.id = o.customer_id
                        WHERE DATE(p.payment_date) = DATE(?) AND (o.hidden = 0 OR o.hidden IS NULL)
                        
                        UNION ALL
                        
                        -- Оплаты из магазина
                        SELECT ss.id, ss.paid_amount as amount, 'cash' as payment_type,
                               COALESCE(ss.sale_date, ss.created_at) as payment_date,
                               NULL as order_id, c.name as client_name,
                               'shop' as payment_source
                        FROM shop_sales ss
                        LEFT JOIN customers c ON c.id = ss.customer_id
                        WHERE DATE(COALESCE(ss.sale_date, ss.created_at)) = DATE(?) AND ss.paid_amount > 0
                        
                        ORDER BY payment_date DESC
                        LIMIT 10
                    ''', [today_moscow, today_moscow])
                elif date_from and date_to:
                    cursor.execute(f'''
                        SELECT p.id, p.amount, p.payment_type, p.payment_date,
                               o.order_id, c.name as client_name,
                               'order' as payment_source
                        FROM payments p
                        JOIN orders o ON o.id = p.order_id
                        LEFT JOIN customers c ON c.id = o.customer_id
                        WHERE DATE(p.payment_date) >= DATE(?) AND DATE(p.payment_date) <= DATE(?) AND (o.hidden = 0 OR o.hidden IS NULL)
                        
                        UNION ALL
                        
                        -- Оплаты из магазина
                        SELECT ss.id, ss.paid_amount as amount, 'cash' as payment_type,
                               COALESCE(ss.sale_date, ss.created_at) as payment_date,
                               NULL as order_id, c.name as client_name,
                               'shop' as payment_source
                        FROM shop_sales ss
                        LEFT JOIN customers c ON c.id = ss.customer_id
                        WHERE DATE(COALESCE(ss.sale_date, ss.created_at)) >= DATE(?) AND DATE(COALESCE(ss.sale_date, ss.created_at)) <= DATE(?) AND ss.paid_amount > 0
                        
                        ORDER BY payment_date DESC
                        LIMIT 10
                    ''', [date_from, date_to, date_from, date_to])
                elif date_from:
                    cursor.execute(f'''
                        SELECT p.id, p.amount, p.payment_type, p.payment_date,
                               o.order_id, c.name as client_name,
                               'order' as payment_source
                        FROM payments p
                        JOIN orders o ON o.id = p.order_id
                        LEFT JOIN customers c ON c.id = o.customer_id
                        WHERE DATE(p.payment_date) >= DATE(?) AND (o.hidden = 0 OR o.hidden IS NULL)
                        
                        UNION ALL
                        
                        -- Оплаты из магазина
                        SELECT ss.id, ss.paid_amount as amount, 'cash' as payment_type,
                               COALESCE(ss.sale_date, ss.created_at) as payment_date,
                               NULL as order_id, c.name as client_name,
                               'shop' as payment_source
                        FROM shop_sales ss
                        LEFT JOIN customers c ON c.id = ss.customer_id
                        WHERE DATE(COALESCE(ss.sale_date, ss.created_at)) >= DATE(?) AND ss.paid_amount > 0
                        
                        ORDER BY payment_date DESC
                        LIMIT 10
                    ''', [date_from, date_from])
                elif date_to:
                    cursor.execute(f'''
                        SELECT p.id, p.amount, p.payment_type, p.payment_date,
                               o.order_id, c.name as client_name,
                               'order' as payment_source
                        FROM payments p
                        JOIN orders o ON o.id = p.order_id
                        LEFT JOIN customers c ON c.id = o.customer_id
                        WHERE DATE(p.payment_date) <= DATE(?) AND (o.hidden = 0 OR o.hidden IS NULL)
                        
                        UNION ALL
                        
                        -- Оплаты из магазина
                        SELECT ss.id, ss.paid_amount as amount, 'cash' as payment_type,
                               COALESCE(ss.sale_date, ss.created_at) as payment_date,
                               NULL as order_id, c.name as client_name,
                               'shop' as payment_source
                        FROM shop_sales ss
                        LEFT JOIN customers c ON c.id = ss.customer_id
                        WHERE DATE(COALESCE(ss.sale_date, ss.created_at)) <= DATE(?) AND ss.paid_amount > 0
                        
                        ORDER BY payment_date DESC
                        LIMIT 10
                    ''', [date_to, date_to])
                else:
                    cursor.execute(f'''
                        SELECT p.id, p.amount, p.payment_type, p.payment_date,
                               o.order_id, c.name as client_name,
                               'order' as payment_source
                        FROM payments p
                        JOIN orders o ON o.id = p.order_id
                        LEFT JOIN customers c ON c.id = o.customer_id
                        WHERE (o.hidden = 0 OR o.hidden IS NULL)
                        
                        UNION ALL
                        
                        -- Оплаты из магазина
                        SELECT ss.id, ss.paid_amount as amount, 'cash' as payment_type,
                               COALESCE(ss.sale_date, ss.created_at) as payment_date,
                               NULL as order_id, c.name as client_name,
                               'shop' as payment_source
                        FROM shop_sales ss
                        LEFT JOIN customers c ON c.id = ss.customer_id
                        WHERE ss.paid_amount > 0
                        
                        ORDER BY payment_date DESC
                        LIMIT 10
                    ''')
                recent_payments = [dict(r) for r in cursor.fetchall()]
                
                return {
                    'date_from': date_from,
                    'date_to': date_to,
                    'orders': orders_stats,
                    'orders_by_status': orders_by_status,
                    'income': income_stats,
                    'warehouse': warehouse_stats,
                    'recent_orders': recent_orders,
                    'recent_payments': recent_payments
                }
                
        except Exception as e:
            logger.error(f"Ошибка при генерации сводного отчета: {e}")
            raise DatabaseError(f"Ошибка при генерации сводного отчета: {e}")

