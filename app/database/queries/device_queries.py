"""
SQL запросы для работы с устройствами.
"""
from typing import Dict, List, Optional
from app.database.connection import get_db_connection, _get_db_driver
import sqlite3
import logging

logger = logging.getLogger(__name__)


class DeviceQueries:
    """Класс для SQL-запросов по устройствам."""

    @staticmethod
    def _agg_concat(expr_sql: str, separator: str = ", ") -> str:
        if _get_db_driver() == "postgres":
            return f"STRING_AGG({expr_sql}, '{separator}')"
        return f"GROUP_CONCAT({expr_sql}, '{separator}')"
    
    @staticmethod
    def get_devices_with_details(
        customer_id: Optional[int] = None,
        device_type_id: Optional[int] = None,
        device_brand_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict:
        """
        Получает список устройств с данными клиента и заявками (оптимизация N+1).
        
        Args:
            customer_id: Фильтр по клиенту
            device_type_id: Фильтр по типу устройства
            device_brand_id: Фильтр по бренду
            page: Номер страницы
            per_page: Количество элементов на странице
            
        Returns:
            Словарь с данными: items, total, page, per_page, pages
        """
        offset = (page - 1) * per_page
        where_clauses = []
        params = []
        
        if customer_id:
            where_clauses.append('d.customer_id = ?')
            params.append(customer_id)
        
        if device_type_id:
            where_clauses.append('d.device_type_id = ?')
            params.append(device_type_id)
        
        if device_brand_id:
            where_clauses.append('d.device_brand_id = ?')
            params.append(device_brand_id)
        
        where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Подсчет общего количества
                count_query = f'''
                    SELECT COUNT(*)
                    FROM devices AS d
                    {where_sql}
                '''
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Получение данных с JOIN
                query = f'''
                    SELECT 
                        d.id,
                        d.customer_id,
                        d.device_type_id,
                        d.device_brand_id,
                        d.serial_number,
                        d.created_at,
                        c.name AS customer_name,
                        c.phone AS customer_phone,
                        dt.name AS device_type,
                        db.name AS device_brand,
                        COUNT(DISTINCT o.id) AS orders_count,
                        MAX(o.created_at) AS last_order_date
                    FROM devices AS d
                    JOIN customers AS c ON c.id = d.customer_id
                    LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                    LEFT JOIN orders AS o ON o.device_id = d.id AND (o.hidden = 0 OR o.hidden IS NULL)
                    {where_sql}
                    GROUP BY d.id
                    ORDER BY d.created_at DESC
                    LIMIT ? OFFSET ?
                '''
                params_with_pagination = params + [per_page, offset]
                cursor.execute(query, params_with_pagination)
                
                rows = cursor.fetchall()
                items = []
                for row in rows:
                    items.append({
                        'id': row['id'],
                        'customer_id': row['customer_id'],
                        'device_type_id': row['device_type_id'],
                        'device_brand_id': row['device_brand_id'],
                        'serial_number': row['serial_number'],
                        'created_at': row['created_at'],
                        'customer_name': row['customer_name'],
                        'customer_phone': row['customer_phone'],
                        'device_type': row['device_type'],
                        'device_brand': row['device_brand'],
                        'orders_count': row['orders_count'] or 0,
                        'last_order_date': row['last_order_date']
                    })
                
                pages = (total + per_page - 1) // per_page if total > 0 else 1
                
                return {
                    'items': items,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': pages
                }
        except Exception as e:
            logger.error(f"Ошибка при получении списка устройств: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_device_orders(device_id: int) -> List[Dict]:
        """
        Получает все заявки по устройству с полными данными.
        
        Args:
            device_id: ID устройства
            
        Returns:
            Список заявок
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                appearance_agg = DeviceQueries._agg_concat("at.name", ", ")
                symptoms_agg = DeviceQueries._agg_concat("s.name", ", ")
                if _get_db_driver() == "postgres":
                    prepayment_amount_expr = "COALESCE(NULLIF(o.prepayment::text, '')::numeric, 0)"
                else:
                    prepayment_amount_expr = "COALESCE(o.prepayment, 0)"
                cursor.execute('''
                    SELECT 
                        o.id,
                        o.order_id,
                        o.created_at,
                        o.updated_at,
                        COALESCE(os.code, o.status) AS status_code,
                        COALESCE(os.name, o.status) AS status_name,
                        COALESCE(os.color, '#6c757d') AS status_color,
                        o.prepayment,
                        o.password,
                        COALESCE(
                            (SELECT ''' + appearance_agg + ''' 
                             FROM order_appearance_tags oat 
                             JOIN appearance_tags at ON at.id = oat.appearance_tag_id 
                             WHERE oat.order_id = o.id),
                            o.appearance
                        ) AS appearance,
                        o.comment,
                        COALESCE(
                            (SELECT ''' + symptoms_agg + ''' 
                             FROM order_symptoms osymp 
                             JOIN symptoms s ON s.id = osymp.symptom_id 
                             WHERE osymp.order_id = o.id),
                            o.symptom_tags
                        ) AS symptom_tags,
                        COALESCE(om.name, o.model) AS model,
                        c.name AS customer_name,
                        c.phone AS customer_phone,
                        c.email AS customer_email,
                        dt.name AS device_type_name,
                        db.name AS device_brand_name,
                        d.serial_number AS device_serial_number,
                        mgr.name AS manager_name,
                        ms.name AS master_name,
                        (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE order_id = o.id) AS total_paid,
                        (SELECT COALESCE(SUM(price * quantity), 0) FROM order_services WHERE order_id = o.id) AS services_total,
                        (SELECT COUNT(*) FROM order_services WHERE order_id = o.id) AS services_count,
                        0 AS parts_count,
                        (SELECT COALESCE(SUM(price * quantity), 0) FROM order_services WHERE order_id = o.id) +
                        ''' + prepayment_amount_expr + ''' AS total_amount
                    FROM orders o
                    LEFT JOIN order_statuses os ON os.id = o.status_id
                    LEFT JOIN customers c ON c.id = o.customer_id
                    LEFT JOIN devices d ON d.id = o.device_id
                    LEFT JOIN device_types dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands db ON db.id = d.device_brand_id
                    LEFT JOIN order_models om ON om.id = o.model_id
                    LEFT JOIN managers mgr ON mgr.id = o.manager_id
                    LEFT JOIN masters ms ON ms.id = o.master_id
                    WHERE o.device_id = ? AND (o.hidden = 0 OR o.hidden IS NULL)
                    ORDER BY o.created_at DESC
                ''', (device_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении заявок устройства {device_id}: {e}", exc_info=True)
            raise

