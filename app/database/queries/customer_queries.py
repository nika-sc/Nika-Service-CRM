"""
SQL запросы для работы с клиентами.
"""
from typing import Dict, List, Optional
from datetime import datetime
from app.database.connection import get_db_connection
from app.utils.datetime_utils import get_moscow_now_naive
from app.utils.validators import normalize_phone
import sqlite3
import logging
import re

logger = logging.getLogger(__name__)


def _phone_search_like_params(search_stripped: str) -> List[str]:
    """
    Подстроки для LIKE по телефону: совпадение при вводе с 8, с 7, только 9…,
    как в БД часто хранят 9XXXXXXXXX без ведущей 7/8.
    """
    raw = (search_stripped or "").strip()
    if not raw:
        return []
    patterns: List[str] = []
    seen = set()

    def add_literal(sub: str) -> None:
        if sub and sub not in seen:
            seen.add(sub)
            patterns.append(f"%{sub}%")

    add_literal(raw)
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return patterns

    add_literal(digits)
    n = normalize_phone(raw)
    if n:
        add_literal(n)
        if n.startswith("7") and len(n) > 1:
            add_literal("8" + n[1:])
        if len(n) >= 10:
            add_literal(n[1:])
    if digits.startswith("8") and len(digits) > 1:
        add_literal(digits[1:])
    if digits.startswith("7") and len(digits) > 1:
        add_literal(digits[1:])

    return patterns


class CustomerQueries:
    """Класс для SQL-запросов по клиентам."""
    
    @staticmethod
    def get_customers_with_details(
        search_query: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
        sort_by: str = 'name',
        sort_order: str = 'ASC'
    ) -> Dict:
        """
        Получает список клиентов с устройствами и заявками (оптимизация N+1).
        
        Args:
            search_query: Поисковый запрос (имя, телефон, email)
            page: Номер страницы
            per_page: Количество элементов на странице
            sort_by: Поле для сортировки (name, phone, email, created_at)
            sort_order: Направление сортировки (ASC, DESC)
            
        Returns:
            Словарь с данными: items, total, page, per_page, pages
        """
        offset = (page - 1) * per_page
        where_clauses = []
        params = []
        
        # Поиск: по ФИО — полнотекстовый (каждое слово в имени); телефон/email — подстрока.
        # Без учёта регистра: SQLite LOWER() не работает для кириллицы, поэтому по имени и email
        # подставляем два варианта паттерна (как введено и в нижнем регистре).
        if search_query:
            search_stripped = search_query.strip()
            search_lower = search_stripped.lower()
            words = [w for w in search_lower.split() if w]
            if words:
                # По имени: все слова должны встречаться; для каждого слова — два варианта (нижний и с заглавной)
                name_conditions = ' AND '.join(
                    ["(COALESCE(c.name, '') LIKE ? OR COALESCE(c.name, '') LIKE ?)" for _ in words]
                )
                name_params = [p for w in words for p in (f'%{w}%', f'%{w.capitalize()}%')]
                phone_like_list = _phone_search_like_params(search_stripped)
                phone_or = " OR ".join(["c.phone LIKE ?"] * len(phone_like_list)) if phone_like_list else "FALSE"
                # Email: два паттерна для нечувствительности к регистру
                where_clauses.append(
                    f"(({name_conditions}) OR ({phone_or}) OR COALESCE(c.email, '') LIKE ? OR COALESCE(c.email, '') LIKE ?)"
                )
                params.extend(name_params + phone_like_list + [f'%{search_stripped}%', f'%{search_lower}%'])
            else:
                phone_like_list = _phone_search_like_params(search_stripped)
                phone_or = " OR ".join(["c.phone LIKE ?"] * len(phone_like_list)) if phone_like_list else "FALSE"
                where_clauses.append(
                    f"(COALESCE(c.name, '') LIKE ? OR COALESCE(c.name, '') LIKE ? OR ({phone_or}) OR COALESCE(c.email, '') LIKE ? OR COALESCE(c.email, '') LIKE ?)"
                )
                params.extend([
                    f'%{search_stripped}%', f'%{search_lower}%',
                    *phone_like_list,
                    f'%{search_stripped}%', f'%{search_lower}%'
                ])
        
        where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        # Маппинг полей сортировки
        sort_column_map = {
            'name': 'c.name',
            'phone': 'c.phone',
            'email': 'c.email',
            'created_at': 'c.created_at'
        }
        order_column = sort_column_map.get(sort_by, 'c.name')
        sort_order = (
            sort_order.upper()
            if sort_order and sort_order.upper() in ('ASC', 'DESC')
            else 'ASC'
        )

        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Подсчет общего количества
                count_query = f'''
                    SELECT COUNT(DISTINCT c.id)
                    FROM customers AS c
                    {where_sql}
                '''
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Получение данных с JOIN для устройств и заявок
                query = f'''
                    SELECT 
                        c.id,
                        c.name,
                        c.phone,
                        c.email,
                        c.created_at,
                        c.updated_at,
                        COUNT(DISTINCT d.id) AS devices_count,
                        COUNT(DISTINCT o.id) AS orders_count,
                        MAX(o.created_at) AS last_order_date
                    FROM customers AS c
                    LEFT JOIN devices AS d ON d.customer_id = c.id
                    LEFT JOIN orders AS o ON o.customer_id = c.id AND (o.hidden = 0 OR o.hidden IS NULL)
                    {where_sql}
                    GROUP BY c.id
                    ORDER BY {order_column} {sort_order}
                    LIMIT ? OFFSET ?
                '''
                params_with_pagination = params + [per_page, offset]
                cursor.execute(query, params_with_pagination)
                
                rows = cursor.fetchall()
                items = []
                for row in rows:
                    items.append({
                        'id': row['id'],
                        'name': row['name'],
                        'phone': row['phone'],
                        'email': row['email'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'devices_count': row['devices_count'] or 0,
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
            logger.error(f"Ошибка при получении списка клиентов: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_customer_statistics(customer_id: int) -> Dict:
        """
        Получает статистику по клиенту.
        
        Args:
            customer_id: ID клиента
            
        Returns:
            Словарь со статистикой
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Основная статистика
                cursor.execute('''
                    SELECT 
                        c.id,
                        c.name,
                        c.phone,
                        c.email,
                        c.created_at,
                        COUNT(DISTINCT d.id) AS devices_count,
                        COUNT(DISTINCT o.id) AS orders_count,
                        COUNT(DISTINCT CASE WHEN o.status_id IS NOT NULL 
                            AND os.code = 'completed' THEN o.id END) AS completed_orders,
                        COUNT(DISTINCT CASE WHEN o.status_id IS NOT NULL 
                            AND os.code = 'in_progress' THEN o.id END) AS in_progress_orders,
                        COUNT(DISTINCT CASE WHEN o.status_id IS NOT NULL 
                            AND os.code = 'new' THEN o.id END) AS new_orders,
                        COALESCE(SUM(p.amount), 0) AS total_paid,
                        COALESCE(SUM(
                            (SELECT COALESCE(SUM(price * quantity), 0) FROM order_services WHERE order_id = o.id) +
                            CASE
                                WHEN TRIM(COALESCE(o.prepayment, '')) = '' THEN 0
                                ELSE CAST(o.prepayment AS REAL)
                            END
                        ), 0) AS total_amount
                    FROM customers AS c
                    LEFT JOIN devices AS d ON d.customer_id = c.id
                    LEFT JOIN orders AS o ON o.customer_id = c.id AND (o.hidden = 0 OR o.hidden IS NULL)
                    LEFT JOIN order_statuses AS os ON os.id = o.status_id
                    LEFT JOIN payments AS p ON p.order_id = o.id
                    WHERE c.id = ?
                    GROUP BY c.id
                ''', (customer_id,))
                
                row = cursor.fetchone()
                if not row:
                    return {}
                
                orders_count = row['orders_count'] or 0
                total_amount = float(row['total_amount'] or 0)
                total_paid = float(row['total_paid'] or 0)
                completed_orders = row['completed_orders'] or 0
                
                # Расчет среднего чека
                average_check = total_amount / orders_count if orders_count > 0 else 0
                
                # Расчет дней с первой заявки
                cursor.execute('''
                    SELECT MIN(created_at) AS first_order_date
                    FROM orders
                    WHERE customer_id = ? AND (hidden = 0 OR hidden IS NULL)
                ''', (customer_id,))
                first_order_row = cursor.fetchone()
                days_since_first = 0
                if first_order_row and first_order_row['first_order_date']:
                    try:
                        first_date = datetime.strptime(first_order_row['first_order_date'], '%Y-%m-%d %H:%M:%S')
                        days_since_first = (get_moscow_now_naive() - first_date).days
                    except (ValueError, TypeError):
                        pass
                
                # Расчет loyalty_score
                loyalty_score = 0
                
                # Баллы за количество заявок
                if orders_count >= 20:
                    loyalty_score += 30
                elif orders_count >= 10:
                    loyalty_score += 20
                elif orders_count >= 5:
                    loyalty_score += 10
                elif orders_count >= 1:
                    loyalty_score += 5
                
                # Баллы за средний чек
                if average_check >= 10000:
                    loyalty_score += 30
                elif average_check >= 5000:
                    loyalty_score += 20
                elif average_check >= 2000:
                    loyalty_score += 10
                elif average_check >= 1000:
                    loyalty_score += 5
                
                # Баллы за частоту обращений
                if orders_count > 1 and days_since_first > 0:
                    frequency = orders_count / max(days_since_first / 30, 1)  # заявок в месяц
                    if frequency >= 2:
                        loyalty_score += 20
                    elif frequency >= 1:
                        loyalty_score += 10
                    elif frequency >= 0.5:
                        loyalty_score += 5
                
                # Баллы за общую сумму
                if total_amount >= 50000:
                    loyalty_score += 20
                elif total_amount >= 20000:
                    loyalty_score += 15
                elif total_amount >= 10000:
                    loyalty_score += 10
                elif total_amount >= 5000:
                    loyalty_score += 5
                
                # Определяем уровень лояльности
                if loyalty_score >= 80:
                    loyalty_level = 'VIP'
                elif loyalty_score >= 60:
                    loyalty_level = 'Постоянный'
                elif loyalty_score >= 40:
                    loyalty_level = 'Активный'
                elif loyalty_score >= 20:
                    loyalty_level = 'Обычный'
                else:
                    loyalty_level = 'Новый'
                
                # Получаем даты первой и последней заявки
                cursor.execute('''
                    SELECT 
                        MIN(created_at) AS first_order_date,
                        MAX(created_at) AS last_order_date
                    FROM orders
                    WHERE customer_id = ? AND (hidden = 0 OR hidden IS NULL)
                ''', (customer_id,))
                date_row = cursor.fetchone()
                first_order_date = date_row['first_order_date'] if date_row and date_row['first_order_date'] else None
                last_order_date = date_row['last_order_date'] if date_row and date_row['last_order_date'] else None
                
                # Вычисляем дни
                days_since_last = 0
                if last_order_date:
                    try:
                        last_date = datetime.strptime(last_order_date, '%Y-%m-%d %H:%M:%S')
                        days_since_last = (get_moscow_now_naive() - last_date).days
                    except (ValueError, TypeError):
                        pass
                
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'phone': row['phone'],
                    'email': row['email'],
                    'created_at': row['created_at'],
                    'devices_count': row['devices_count'] or 0,
                    'orders_count': orders_count,
                    'completed_orders': completed_orders,
                    'in_progress_orders': row['in_progress_orders'] or 0,
                    'new_orders': row['new_orders'] or 0,
                    'total_paid': total_paid,
                    'paid_amount': total_paid,  # Для обратной совместимости
                    'total_amount': total_amount,
                    'debt': total_amount - total_paid,
                    'debt_amount': total_amount - total_paid,  # Для обратной совместимости
                    'average_check': average_check,
                    'loyalty_score': min(loyalty_score, 100),  # Ограничиваем до 100
                    'loyalty_level': loyalty_level,
                    'first_order_date': first_order_date,
                    'last_order_date': last_order_date,
                    'days_since_first': days_since_first,
                    'days_since_last': days_since_last
                }
        except Exception as e:
            logger.error(f"Ошибка при получении статистики клиента {customer_id}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def search_customers(query: str, limit: int = 10) -> List[Dict]:
        """
        Быстрый поиск клиентов по имени, телефону или email.
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            Список клиентов
        """
        if not query or len(query) < 2:
            return []
        
        query_stripped = query.strip()
        query_lower = query_stripped.lower()
        # Без LOWER() в SQL: SQLite не переводит кириллицу, поэтому два паттерна (как введено и нижний регистр)
        search_pattern = f'%{query_stripped}%'
        search_lower = f'%{query_lower}%'
        phone_like_list = _phone_search_like_params(query_stripped)
        phone_or = " OR ".join(["phone LIKE ?"] * len(phone_like_list)) if phone_like_list else "FALSE"
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT 
                        id,
                        name,
                        phone,
                        email
                    FROM customers
                    WHERE (COALESCE(name, '') LIKE ? OR COALESCE(name, '') LIKE ?)
                       OR ({phone_or})
                       OR (COALESCE(email, '') LIKE ? OR COALESCE(email, '') LIKE ?)
                    ORDER BY name
                    LIMIT ?
                ''', (search_pattern, search_lower, *phone_like_list, search_pattern, search_lower, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при поиске клиентов: {e}", exc_info=True)
            return []

