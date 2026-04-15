"""
Сервис для работы с шаблонами заявок.
"""
from typing import Optional, Dict, List
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
import sqlite3
import logging
import json

logger = logging.getLogger(__name__)


class TemplateService:
    """Сервис для работы с шаблонами заявок."""
    
    @staticmethod
    def create_template(
        name: str,
        template_data: Dict,
        created_by: int,
        description: Optional[str] = None,
        is_public: bool = False
    ) -> int:
        """Создает шаблон заявки."""
        if not name or not name.strip():
            raise ValidationError("Название шаблона обязательно")
        
        if template_data is None:
            template_data = {}
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO order_templates 
                    (name, description, template_data, created_by, is_public, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (name.strip(), description, json.dumps(template_data), created_by, int(is_public)))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при создании шаблона: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
    
    @staticmethod
    def get_template(template_id: int) -> Optional[Dict]:
        """Получает шаблон по ID."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT t.*, u.display_name as created_by_name
                    FROM order_templates t
                    LEFT JOIN users u ON u.id = t.created_by
                    WHERE t.id = ?
                ''', (template_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                
                template = dict(row)
                template['template_data'] = json.loads(template['template_data'])
                return template
        except Exception as e:
            logger.error(f"Ошибка при получении шаблона {template_id}: {e}")
            return None
    
    @staticmethod
    def get_templates(user_id: Optional[int] = None, include_public: bool = True) -> List[Dict]:
        """Получает список шаблонов."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                query = 'SELECT t.*, u.display_name as created_by_name FROM order_templates t LEFT JOIN users u ON u.id = t.created_by WHERE 1=1'
                params = []
                
                if user_id:
                    query += ' AND (t.created_by = ? OR t.is_public = 1)'
                    params.append(user_id)
                elif not include_public:
                    query += ' AND t.is_public = 0'
                
                query += ' ORDER BY t.created_at DESC'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                templates = []
                for row in rows:
                    template = dict(row)
                    try:
                        template['template_data'] = json.loads(template['template_data'])
                    except (json.JSONDecodeError, TypeError):
                        template['template_data'] = {}
                    templates.append(template)
                
                return templates
        except Exception as e:
            logger.error(f"Ошибка при получении шаблонов: {e}")
            return []
    
    @staticmethod
    def update_template(
        template_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        template_data: Optional[Dict] = None,
        is_public: Optional[bool] = None
    ) -> bool:
        """Обновляет шаблон."""
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name.strip())
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if template_data is not None:
            updates.append("template_data = ?")
            params.append(json.dumps(template_data))
        if is_public is not None:
            updates.append("is_public = ?")
            params.append(int(is_public))
        
        if not updates:
            return True
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(template_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE order_templates
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при обновлении шаблона {template_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
    
    @staticmethod
    def delete_template(template_id: int) -> bool:
        """Удаляет шаблон."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM order_templates WHERE id = ?', (template_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при удалении шаблона {template_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
