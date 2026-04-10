"""
SQL запросы для работы с комментариями.
"""
from typing import Dict, List, Optional
from app.database.connection import get_db_connection, _get_db_driver
import sqlite3
import logging

logger = logging.getLogger(__name__)


class CommentQueries:
    """Класс для SQL-запросов по комментариям."""

    @staticmethod
    def _attachments_agg_sql() -> str:
        expr = "a.id || ':' || a.filename || ':' || a.file_path"
        if _get_db_driver() == "postgres":
            return f"STRING_AGG({expr}, ',')"
        return f"GROUP_CONCAT({expr})"
    
    @staticmethod
    def get_order_comments(order_id: int) -> List[Dict]:
        """
        Получает комментарии заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список комментариев
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                attachments_agg = CommentQueries._attachments_agg_sql()
                query = f'''
                    SELECT 
                        c.id,
                        c.order_id,
                        c.author_name,
                        c.comment_text,
                        c.user_id,
                        c.is_internal,
                        c.mentions,
                        c.created_at,
                        {attachments_agg} as attachments
                    FROM order_comments c
                    LEFT JOIN comment_attachments a ON a.comment_id = c.id
                    WHERE c.order_id = ?
                    GROUP BY c.id
                    ORDER BY c.created_at DESC
                '''
                cursor.execute(query, (order_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении комментариев заявки {order_id}: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_comments_batch(order_ids: List[int]) -> Dict[int, List[Dict]]:
        """
        Получает комментарии для нескольких заявок одним запросом (оптимизация N+1).
        
        Args:
            order_ids: Список ID заявок
            
        Returns:
            Словарь {order_id: [комментарии]}
        """
        if not order_ids:
            return {}
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                attachments_agg = CommentQueries._attachments_agg_sql()
                
                # Создаем плейсхолдеры для IN запроса
                placeholders = ','.join('?' * len(order_ids))
                query = f'''
                    SELECT 
                        c.id,
                        c.order_id,
                        c.author_name,
                        c.comment_text,
                        c.user_id,
                        c.is_internal,
                        c.mentions,
                        c.created_at,
                        {attachments_agg} as attachments
                    FROM order_comments c
                    LEFT JOIN comment_attachments a ON a.comment_id = c.id
                    WHERE c.order_id IN ({placeholders})
                    GROUP BY c.id
                    ORDER BY c.order_id, c.created_at DESC
                '''
                cursor.execute(query, order_ids)
                
                rows = cursor.fetchall()
                
                # Группируем комментарии по order_id
                comments_by_order = {}
                for row in rows:
                    order_id = row['order_id']
                    if order_id not in comments_by_order:
                        comments_by_order[order_id] = []
                    comments_by_order[order_id].append(dict(row))
                
                return comments_by_order
        except Exception as e:
            logger.error(f"Ошибка при получении комментариев для заявок: {e}", exc_info=True)
            return {}

