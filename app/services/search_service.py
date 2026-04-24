"""
Сервис для глобального поиска.
"""
from typing import Dict, List, Optional
from app.database.connection import get_db_connection, _get_db_driver
import sqlite3
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """Сервис для глобального поиска."""
    
    @staticmethod
    def global_search(query: str, limit: int = 50, entity_types: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """
        Выполняет глобальный поиск по всем сущностям.
        
        Args:
            query: Поисковый запрос
            limit: Лимит результатов на тип сущности
            entity_types: Список типов для поиска (orders, customers, parts). Если None, ищет по всем.
            
        Returns:
            Словарь {entity_type: [результаты]}
        """
        if not query or not query.strip():
            return {}
        
        search_query = query.strip()
        results = {}
        
        # Поиск по заявкам
        if not entity_types or 'orders' in entity_types:
            try:
                results['orders'] = SearchService._search_orders(search_query, limit)
            except Exception as e:
                logger.error(f"Ошибка поиска по заявкам: {e}")
                results['orders'] = []
        
        # Поиск по клиентам
        if not entity_types or 'customers' in entity_types:
            try:
                results['customers'] = SearchService._search_customers(search_query, limit)
            except Exception as e:
                logger.error(f"Ошибка поиска по клиентам: {e}")
                results['customers'] = []
        
        # Поиск по товарам
        if not entity_types or 'parts' in entity_types:
            try:
                results['parts'] = SearchService._search_parts(search_query, limit)
            except Exception as e:
                logger.error(f"Ошибка поиска по товарам: {e}")
                results['parts'] = []
        
        return results
    
    @staticmethod
    def _looks_like_uuid(q: str) -> bool:
        """Проверяет, похож ли запрос на UUID или часть UUID (hex + возможно дефисы)."""
        if not q or len(q) < 4:
            return False
        s = q.replace('-', '')
        return len(s) >= 4 and all(c in '0123456789abcdefABCDEF' for c in s)

    @staticmethod
    def _search_orders(query: str, limit: int) -> List[Dict]:
        """Поиск по заявкам через FTS. При вводе только цифр или UUID — сразу fallback (id или order_id)."""
        query_stripped = query.strip()
        if query_stripped.isdigit():
            return SearchService._search_orders_fallback(query_stripped, limit)
        if SearchService._looks_like_uuid(query_stripped):
            return SearchService._search_orders_fallback(query_stripped, limit)
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                if _get_db_driver() == 'postgres':
                    cursor.execute('''
                        SELECT
                            o.id,
                            o.order_id,
                            o.created_at,
                            c.name as client_name,
                            c.phone,
                            os.name as status_name,
                            os.color as status_color
                        FROM orders o
                        JOIN customers c ON c.id = o.customer_id
                        LEFT JOIN order_statuses os ON os.id = o.status_id
                        LEFT JOIN devices d ON d.id = o.device_id
                        LEFT JOIN device_types dt ON dt.id = d.device_type_id
                        LEFT JOIN device_brands db ON db.id = d.device_brand_id
                        WHERE (o.hidden = 0 OR o.hidden IS NULL)
                          AND to_tsvector(
                                'simple',
                                concat_ws(' ',
                                    COALESCE(o.order_id, ''),
                                    COALESCE(c.name, ''),
                                    COALESCE(c.phone, ''),
                                    COALESCE(c.email, ''),
                                    COALESCE(d.serial_number, ''),
                                    COALESCE(dt.name, ''),
                                    COALESCE(db.name, ''),
                                    COALESCE(o.comment, ''),
                                    COALESCE(o.symptom_tags, ''),
                                    COALESCE(o.appearance, '')
                                )
                              ) @@ websearch_to_tsquery('simple', %s)
                        ORDER BY o.created_at DESC
                        LIMIT %s
                    ''', (query_stripped, limit))
                else:
                    cursor.execute('''
                        SELECT 
                            o.id,
                            o.order_id,
                            o.created_at,
                            c.name as client_name,
                            c.phone,
                            os.name as status_name,
                            os.color as status_color
                        FROM orders_fts fts
                        JOIN orders o ON o.id = fts.rowid
                        JOIN customers c ON c.id = o.customer_id
                        LEFT JOIN order_statuses os ON os.id = o.status_id
                        WHERE orders_fts MATCH ?
                        AND (o.hidden = 0 OR o.hidden IS NULL)
                        ORDER BY rank
                        LIMIT ?
                    ''', (f'{query_stripped}*', limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка FTS поиска по заявкам: {e}")
            return SearchService._search_orders_fallback(query_stripped, limit)
    
    @staticmethod
    def _search_orders_fallback(query: str, limit: int) -> List[Dict]:
        """Fallback поиск по заявкам без FTS. Поддерживает поиск по номеру заявки (id) и по order_id (#4782)."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                search_pattern = f'%{query}%'
                params = [search_pattern, search_pattern, search_pattern, search_pattern, search_pattern]
                id_condition = ' OR o.id = ?'
                if query.isdigit():
                    params.append(int(query))
                else:
                    params.append(-1)
                params.append(limit)
                cursor.execute('''
                    SELECT DISTINCT
                        o.id,
                        o.order_id,
                        o.created_at,
                        c.name as client_name,
                        c.phone,
                        os.name as status_name,
                        os.color as status_color
                    FROM orders o
                    JOIN customers c ON c.id = o.customer_id
                    LEFT JOIN order_statuses os ON os.id = o.status_id
                    WHERE (o.hidden = 0 OR o.hidden IS NULL)
                    AND (
                        o.order_id LIKE ? OR
                        c.name LIKE ? OR
                        c.phone LIKE ? OR
                        c.email LIKE ? OR
                        o.comment LIKE ?
                        ''' + id_condition + '''
                    )
                    ORDER BY o.created_at DESC
                    LIMIT ?
                ''', tuple(params))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка fallback поиска по заявкам: {e}")
            return []
    
    @staticmethod
    def _search_customers(query: str, limit: int) -> List[Dict]:
        """Поиск по клиентам через FTS."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                if _get_db_driver() == 'postgres':
                    cursor.execute('''
                        SELECT
                            c.id,
                            c.name,
                            c.phone,
                            c.email,
                            c.created_at
                        FROM customers c
                        WHERE to_tsvector('simple', concat_ws(' ', COALESCE(c.name, ''), COALESCE(c.phone, ''), COALESCE(c.email, '')))
                              @@ websearch_to_tsquery('simple', %s)
                        ORDER BY c.created_at DESC
                        LIMIT %s
                    ''', (query, limit))
                else:
                    cursor.execute('''
                        SELECT 
                            c.id,
                            c.name,
                            c.phone,
                            c.email,
                            c.created_at
                        FROM customers_fts fts
                        JOIN customers c ON c.id = fts.rowid
                        WHERE customers_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                    ''', (f'{query}*', limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка FTS поиска по клиентам: {e}")
            # Fallback
            return SearchService._search_customers_fallback(query, limit)
    
    @staticmethod
    def _search_customers_fallback(query: str, limit: int) -> List[Dict]:
        """Fallback поиск по клиентам."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                search_pattern = f'%{query}%'
                cursor.execute('''
                    SELECT id, name, phone, email, created_at
                    FROM customers
                    WHERE name LIKE ? OR phone LIKE ? OR email LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (search_pattern, search_pattern, search_pattern, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка fallback поиска по клиентам: {e}")
            return []
    
    @staticmethod
    def _search_parts(query: str, limit: int) -> List[Dict]:
        """Поиск по товарам через FTS."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                if _get_db_driver() == 'postgres':
                    cursor.execute('''
                        SELECT
                            p.id,
                            p.name,
                            p.part_number,
                            p.price,
                            p.stock_quantity,
                            pc.name as category_name
                        FROM parts p
                        LEFT JOIN part_categories pc ON pc.id = p.category_id
                        WHERE to_tsvector('simple', concat_ws(' ', COALESCE(p.name, ''), COALESCE(p.part_number, ''), COALESCE(p.description, '')))
                              @@ websearch_to_tsquery('simple', %s)
                        ORDER BY p.name
                        LIMIT %s
                    ''', (query, limit))
                else:
                    cursor.execute('''
                        SELECT 
                            p.id,
                            p.name,
                            p.part_number,
                            p.price,
                            p.stock_quantity,
                            pc.name as category_name
                        FROM parts_fts fts
                        JOIN parts p ON p.id = fts.rowid
                        LEFT JOIN part_categories pc ON pc.id = p.category_id
                        WHERE parts_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?
                    ''', (f'{query}*', limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка FTS поиска по товарам: {e}")
            # Fallback
            return SearchService._search_parts_fallback(query, limit)
    
    @staticmethod
    def _search_parts_fallback(query: str, limit: int) -> List[Dict]:
        """Fallback поиск по товарам."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                search_pattern = f'%{query}%'
                cursor.execute('''
                    SELECT p.id, p.name, p.part_number, p.price, p.stock_quantity, pc.name as category_name
                    FROM parts p
                    LEFT JOIN part_categories pc ON pc.id = p.category_id
                    WHERE p.name LIKE ? OR p.part_number LIKE ? OR COALESCE(p.description, '') LIKE ?
                    ORDER BY p.name
                    LIMIT ?
                ''', (search_pattern, search_pattern, search_pattern, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка fallback поиска по товарам: {e}")
            return []
    
    @staticmethod
    def autocomplete(query: str, entity_type: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Автодополнение для поиска.
        
        Args:
            query: Поисковый запрос
            entity_type: Тип сущности (orders, customers, parts) или None для всех
            limit: Лимит результатов
            
        Returns:
            Список результатов для автодополнения
        """
        if not query or len(query) < 2:
            return []
        
        results = []
        
        if not entity_type or entity_type == 'orders':
            orders = SearchService._search_orders(query, limit)
            results.extend([{'type': 'order', 'id': o['id'], 'text': f"Заявка #{o['id']} - {o.get('client_name', '')}"} for o in orders[:5]])
        
        if not entity_type or entity_type == 'customers':
            customers = SearchService._search_customers(query, limit)
            results.extend(
                [
                    {
                        'type': 'customer',
                        'id': c['id'],
                        'text': f"{c.get('name') or '—'} ({c.get('phone') or '—'})",
                    }
                    for c in customers[:5]
                ]
            )
        
        if not entity_type or entity_type == 'parts':
            parts = SearchService._search_parts(query, limit)
            results.extend([{'type': 'part', 'id': p['id'], 'text': f"{p['name']} ({p.get('part_number', '')})"} for p in parts[:5]])
        
        return results[:limit]
