"""
Сервис для работы с комментариями.
"""
from typing import Optional, Dict, List
from app.database.queries.comment_queries import CommentQueries
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)


class CommentService:
    """Сервис для работы с комментариями."""
    
    @staticmethod
    def get_order_comments(order_id: int) -> List[Dict]:
        """
        Получает комментарии заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список комментариев
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        return CommentQueries.get_order_comments(order_id)
    
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
        
        return CommentQueries.get_comments_batch(order_ids)
    
    @staticmethod
    def parse_mentions(comment_text: str) -> List[int]:
        """
        Парсит упоминания пользователей в тексте комментария (@username).
        
        Args:
            comment_text: Текст комментария
            
        Returns:
            Список ID упомянутых пользователей
        """
        import re
        from app.services.user_service import UserService
        
        # Ищем упоминания вида @username
        mentions_pattern = r'@(\w+)'
        matches = re.findall(mentions_pattern, comment_text)
        
        mentioned_user_ids = []
        for username in matches:
            user = UserService.get_user_by_username(username)
            if user:
                mentioned_user_ids.append(user['id'])
        
        return mentioned_user_ids
    
    @staticmethod
    def add_comment(
        order_id: int,
        author_name: str,
        comment_text: str,
        user_id: Optional[int] = None,
        is_internal: bool = False,
        attachment_ids: Optional[List[int]] = None
    ) -> int:
        """
        Добавляет комментарий к заявке.
        
        Args:
            order_id: ID заявки
            author_name: Имя автора
            comment_text: Текст комментария
            
        Returns:
            ID созданного комментария
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если заявка не найдена
            DatabaseError: Если произошла ошибка БД
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        if not author_name or not author_name.strip():
            raise ValidationError("Имя автора обязательно")
        
        if not comment_text or not comment_text.strip():
            raise ValidationError("Текст комментария обязателен")
        
        # Проверяем существование заявки
        from app.services.order_service import OrderService
        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        # Парсим упоминания
        mentioned_user_ids = CommentService.parse_mentions(comment_text)
        mentions_json = None
        if mentioned_user_ids:
            import json
            mentions_json = json.dumps(mentioned_user_ids)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO order_comments 
                    (order_id, author_name, comment_text, user_id, is_internal, mentions, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (order_id, author_name.strip(), comment_text.strip(), user_id, int(is_internal), mentions_json))
                conn.commit()
                
                comment_id = cursor.lastrowid
                
                # Сохраняем вложения, если есть
                if attachment_ids:
                    for attachment_id in attachment_ids:
                        cursor.execute('''
                            UPDATE comment_attachments
                            SET comment_id = ?
                            WHERE id = ? AND comment_id IS NULL
                        ''', (comment_id, attachment_id))
                    conn.commit()
                
                # Отправляем уведомления упомянутым пользователям
                if mentioned_user_ids:
                    try:
                        from app.services.notification_service import NotificationService
                        for mentioned_user_id in mentioned_user_ids:
                            NotificationService.send_in_app_notification(
                                user_id=mentioned_user_id,
                                title=f"Вас упомянули в комментарии к заявке #{order_id}",
                                message=f"{author_name.strip()}: {comment_text.strip()[:100]}...",
                                entity_type='order',
                                entity_id=order_id
                            )
                    except Exception as e:
                        logger.warning(f"Не удалось отправить уведомления упомянутым пользователям: {e}")
                
                # Логируем добавление комментария
                try:
                    from app.services.action_log_service import ActionLogService
                    ActionLogService.log_action(
                        user_id=None,
                        username=author_name.strip(),
                        action_type='create',
                        entity_type='comment',
                        entity_id=comment_id,
                        description=f"Добавлен комментарий к заявке #{order_id}",
                        details={
                            'ID заявки': order_id,
                            'Автор': author_name.strip(),
                            'Текст': comment_text.strip()[:100] + '...' if len(comment_text.strip()) > 100 else comment_text.strip()
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать добавление комментария: {e}")
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                
                return comment_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при добавлении комментария к заявке {order_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при добавлении комментария: {e}")
            raise DatabaseError(f"Ошибка при добавлении комментария: {e}")
    
    @staticmethod
    def delete_comment(comment_id: int) -> bool:
        """
        Удаляет комментарий.
        
        Args:
            comment_id: ID комментария
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если комментарий не найден
            DatabaseError: Если произошла ошибка БД
        """
        if not comment_id or comment_id <= 0:
            raise ValidationError("Неверный ID комментария")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM order_comments WHERE id = ?', (comment_id,))
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Комментарий с ID {comment_id} не найден")
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                
                return True
        except (ValidationError, NotFoundError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при удалении комментария {comment_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при удалении комментария: {e}")
            raise DatabaseError(f"Ошибка при удалении комментария: {e}")

