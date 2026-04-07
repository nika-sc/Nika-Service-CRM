"""
SQL запросы для работы с оплатами.
"""
from typing import Dict, List, Optional
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)


class PaymentQueries:
    """Класс для SQL-запросов по оплатам."""
    
    @staticmethod
    def get_order_payments(order_id: int) -> List[Dict]:
        """
        Получает все оплаты по заявке.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список оплат
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()

                # Устойчиво к разным версиям схемы (до/после 027)
                cursor.execute("PRAGMA table_info(payments)")
                cols = [r[1] for r in cursor.fetchall()]

                select_cols = [
                    "id",
                    "order_id",
                    "amount",
                    "payment_type",
                ]
                optional_cols = [
                    "kind",
                    "status",
                    "refunded_of_id",
                    "idempotency_key",
                    "is_cancelled",
                ]
                for c in optional_cols:
                    if c in cols:
                        select_cols.append(c)

                # всегда существующие исторически
                select_cols += [
                    "payment_date",
                    "created_by",
                    "created_by_username",
                    "comment",
                    "created_at",
                ]

                cursor.execute(
                    f"""
                    SELECT {", ".join(select_cols)}
                    FROM payments
                    WHERE order_id = ?
                    ORDER BY payment_date DESC, created_at DESC
                    """,
                    (order_id,),
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении оплат заявки {order_id}: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_customer_payments(customer_id: int, limit: int = 50) -> List[Dict]:
        """
        Получает все оплаты клиента.
        
        Args:
            customer_id: ID клиента
            limit: Максимальное количество записей
            
        Returns:
            Список оплат
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        p.id,
                        p.order_id,
                        p.amount,
                        p.payment_type,
                        p.payment_date,
                        p.created_by,
                        p.created_by_username,
                        p.comment,
                        p.created_at,
                        o.order_id AS order_uuid
                    FROM payments AS p
                    JOIN orders AS o ON o.id = p.order_id
                    WHERE o.customer_id = ?
                    ORDER BY p.payment_date DESC, p.created_at DESC
                    LIMIT ?
                ''', (customer_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении оплат клиента {customer_id}: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_payment_statistics(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        payment_type: Optional[str] = None
    ) -> Dict:
        """
        Получает статистику по оплатам.
        
        Args:
            start_date: Дата начала (YYYY-MM-DD)
            end_date: Дата окончания (YYYY-MM-DD)
            payment_type: Тип оплаты
            
        Returns:
            Словарь со статистикой
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                where_clauses = []
                params = []
                
                if start_date:
                    where_clauses.append('DATE(payment_date) >= ?')
                    params.append(start_date)
                
                if end_date:
                    where_clauses.append('DATE(payment_date) <= ?')
                    params.append(end_date)
                
                if payment_type:
                    where_clauses.append('payment_type = ?')
                    params.append(payment_type)
                
                where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
                
                cursor.execute(f'''
                    SELECT 
                        COUNT(*) AS total_payments,
                        COALESCE(SUM(amount), 0) AS total_amount,
                        COALESCE(AVG(amount), 0) AS avg_amount,
                        COALESCE(MAX(amount), 0) AS max_amount,
                        COALESCE(MIN(amount), 0) AS min_amount,
                        COUNT(DISTINCT order_id) AS orders_count,
                        COUNT(DISTINCT CASE WHEN payment_type = 'cash' THEN id END) AS cash_count,
                        COUNT(DISTINCT CASE WHEN payment_type = 'card' THEN id END) AS card_count,
                        COUNT(DISTINCT CASE WHEN payment_type = 'transfer' THEN id END) AS transfer_count
                    FROM payments
                    {where_sql}
                ''', params)
                
                row = cursor.fetchone()
                if not row:
                    return {}
                
                return {
                    'total_payments': row['total_payments'] or 0,
                    'total_amount': float(row['total_amount'] or 0),
                    'avg_amount': float(row['avg_amount'] or 0),
                    'max_amount': float(row['max_amount'] or 0),
                    'min_amount': float(row['min_amount'] or 0),
                    'orders_count': row['orders_count'] or 0,
                    'cash_count': row['cash_count'] or 0,
                    'card_count': row['card_count'] or 0,
                    'transfer_count': row['transfer_count'] or 0
                }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики оплат: {e}", exc_info=True)
            return {}

