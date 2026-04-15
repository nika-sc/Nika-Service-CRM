"""
SQL запросы для работы со справочниками.
"""
from typing import Dict, List, Optional
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)


class ReferenceQueries:
    """Класс для SQL-запросов по справочникам."""

    @staticmethod
    def _parts_price_column(cursor) -> str:
        """Возвращает актуальное имя колонки цены в таблице parts."""
        cursor.execute("PRAGMA table_info(parts)")
        columns = {row[1] for row in cursor.fetchall()}
        if "retail_price" in columns:
            return "retail_price"
        return "price"
    
    @staticmethod
    def get_all_references() -> Dict:
        """
        Получает все справочники одним запросом (batch-запрос).
        
        Returns:
            Словарь со всеми справочниками
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                parts_price_col = ReferenceQueries._parts_price_column(cursor)
                
                # Получаем все справочники параллельно
                device_types = cursor.execute('''
                    SELECT id, name, sort_order 
                    FROM device_types 
                    ORDER BY sort_order, name
                ''').fetchall()
                
                device_brands = cursor.execute('''
                    SELECT id, name, sort_order 
                    FROM device_brands 
                    ORDER BY sort_order, name
                ''').fetchall()
                
                managers = cursor.execute('''
                    SELECT id, name 
                    FROM managers 
                    ORDER BY name
                ''').fetchall()
                
                masters = cursor.execute('''
                    SELECT id, name 
                    FROM masters 
                    ORDER BY name
                ''').fetchall()
                
                symptoms = cursor.execute('''
                    SELECT id, name, sort_order 
                    FROM symptoms 
                    ORDER BY sort_order, name
                ''').fetchall()
                
                appearance_tags = cursor.execute('''
                    SELECT id, name, sort_order 
                    FROM appearance_tags 
                    ORDER BY sort_order, name
                ''').fetchall()
                
                services = cursor.execute('''
                    SELECT id, name, price, is_default, sort_order 
                    FROM services 
                    ORDER BY sort_order, name
                ''').fetchall()
                
                parts = cursor.execute(f'''
                    SELECT id, name, part_number, {parts_price_col} AS price, stock_quantity, category 
                    FROM parts 
                    WHERE is_deleted = 0
                    ORDER BY name
                ''').fetchall()
                
                order_statuses = cursor.execute('''
                    SELECT id, code, name, color, is_default, sort_order,
                           group_name, triggers_payment_modal, accrues_salary,
                           is_archived, is_final, blocks_edit,
                           requires_warranty, requires_comment
                    FROM order_statuses
                    WHERE is_archived = 0 OR is_archived IS NULL
                    ORDER BY sort_order, name
                ''').fetchall()

                # Модели устройств для заявок (для автодополнения в /add_order)
                order_models = cursor.execute('''
                    SELECT id, name
                    FROM order_models
                    ORDER BY name
                ''').fetchall()
                
                return {
                    'device_types': [dict(row) for row in device_types],
                    'device_brands': [dict(row) for row in device_brands],
                    'managers': [dict(row) for row in managers],
                    'masters': [dict(row) for row in masters],
                    'symptoms': [dict(row) for row in symptoms],
                    'appearance_tags': [dict(row) for row in appearance_tags],
                    'services': [dict(row) for row in services],
                    'parts': [dict(row) for row in parts],
                    'order_statuses': [dict(row) for row in order_statuses],
                    'order_models': [dict(row) for row in order_models],
                }
        except Exception as e:
            logger.error(f"Ошибка при получении справочников: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_device_types() -> List[Dict]:
        """Получает типы устройств."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                parts_price_col = ReferenceQueries._parts_price_column(cursor)
                cursor.execute('''
                    SELECT id, name, sort_order 
                    FROM device_types 
                    ORDER BY sort_order, name
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении типов устройств: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_device_brands() -> List[Dict]:
        """Получает бренды устройств."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, sort_order 
                    FROM device_brands 
                    ORDER BY sort_order, name
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении брендов устройств: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_managers() -> List[Dict]:
        """Получает менеджеров."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, name FROM managers ORDER BY name')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении менеджеров: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_masters() -> List[Dict]:
        """Получает мастеров."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, name FROM masters ORDER BY name')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении мастеров: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_symptoms() -> List[Dict]:
        """Получает симптомы."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, sort_order 
                    FROM symptoms 
                    ORDER BY sort_order, name
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении симптомов: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_appearance_tags() -> List[Dict]:
        """Получает теги внешнего вида."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, sort_order 
                    FROM appearance_tags 
                    ORDER BY sort_order, name
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении тегов внешнего вида: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_services() -> List[Dict]:
        """Получает услуги."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, price, is_default, sort_order, salary_rule_type, salary_rule_value
                    FROM services
                    ORDER BY sort_order, name
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении услуг: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_parts(search_query: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
        """Получает запчасти."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                where_clauses = ['is_deleted = 0']  # Исключаем удаленные товары
                params = []
                
                if search_query:
                    search_pattern = f'%{search_query}%'
                    where_clauses.append('(name LIKE ? OR part_number LIKE ?)')
                    params.extend([search_pattern, search_pattern])
                
                if category:
                    where_clauses.append('category = ?')
                    params.append(category)
                
                where_sql = 'WHERE ' + ' AND '.join(where_clauses)
                
                query = f'''
                    SELECT id, name, part_number, {parts_price_col} AS price, stock_quantity, category 
                    FROM parts 
                    {where_sql}
                    ORDER BY name
                '''
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении запчастей: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_order_statuses(include_archived: bool = False) -> List[Dict]:
        """Получает статусы заявок."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                query = '''
                    SELECT id, code, name, color, is_default, sort_order,
                           group_name, triggers_payment_modal, accrues_salary,
                           is_archived, is_final, blocks_edit,
                           requires_warranty, requires_comment
                    FROM order_statuses
                '''
                if not include_archived:
                    query += ' WHERE is_archived = 0 OR is_archived IS NULL'
                query += ' ORDER BY sort_order, name'
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении статусов заявок: {e}", exc_info=True)
            return []

