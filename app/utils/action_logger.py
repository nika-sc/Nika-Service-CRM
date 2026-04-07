"""
Декоратор для автоматического логирования действий.
"""
from functools import wraps
from typing import Callable, Any, Optional
from flask_login import current_user
from app.services.action_log_service import ActionLogService
import logging

logger = logging.getLogger(__name__)


def log_action_decorator(action_type: str, entity_type: str):
    """
    Декоратор для автоматического логирования действий.
    
    Args:
        action_type: Тип действия (create, update, delete, view)
        entity_type: Тип сущности (order, customer, part)
        
    Usage:
        @log_action_decorator('create', 'order')
        def create_order():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Выполняем функцию
                result = func(*args, **kwargs)
                
                # Логируем действие
                user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
                username = current_user.username if hasattr(current_user, 'username') and current_user.is_authenticated else None
                
                # Пытаемся извлечь entity_id из результата или аргументов
                entity_id = None
                if isinstance(result, dict) and 'id' in result:
                    entity_id = result['id']
                elif isinstance(result, dict) and 'order_id' in result:
                    # Для заявок может быть order_id
                    pass
                elif args and len(args) > 0:
                    # Первый аргумент может быть ID
                    try:
                        entity_id = int(args[0])
                    except (ValueError, TypeError, IndexError):
                        pass
                
                ActionLogService.log_action(
                    user_id=user_id,
                    username=username,
                    action_type=action_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    description=f"{action_type.capitalize()} {entity_type}"
                )
                
                return result
            except Exception as e:
                logger.error(f"Ошибка при логировании действия {action_type} {entity_type}: {e}")
                # Продолжаем выполнение даже если логирование не удалось
                raise
        return wrapper
    return decorator

