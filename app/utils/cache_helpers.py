"""
Вспомогательные функции для работы с кэшем справочников.
"""
from app.services.reference_service import ReferenceService
import logging

logger = logging.getLogger(__name__)


def clear_reference_cache(reference_type: str = None):
    """
    Очищает кэш справочников.
    
    Args:
        reference_type: Тип справочника ('device_types', 'device_brands', 'symptoms', 
                        'appearance_tags', 'services', 'order_statuses', 'parts').
                        Если None, очищает все справочники.
    """
    if reference_type:
        # Очищаем конкретный справочник
        cache_prefixes = {
            'device_types': 'ref_device_types',
            'device_brands': 'ref_device_brands',
            'symptoms': 'ref_symptoms',
            'appearance_tags': 'ref_appearance_tags',
            'services': 'ref_services',
            'order_statuses': 'ref_order_statuses',
            'parts': 'ref_parts',
            'part_categories': 'ref_part_categories',
        }
        
        if reference_type in cache_prefixes:
            from app.utils.cache import clear_cache
            clear_cache(key_prefix=cache_prefixes[reference_type])
            logger.info(f"Кэш справочника '{reference_type}' очищен")
    else:
        # Очищаем все справочники
        ReferenceService.clear_all_cache()


def with_cache_clear(reference_type: str):
    """
    Декоратор для очистки кэша после изменения справочника.
    
    Args:
        reference_type: Тип справочника для очистки кэша
        
    Usage:
        @with_cache_clear('device_types')
        def add_device_type(name):
            ...
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Очищаем кэш после успешного изменения
            if result:  # Если операция успешна
                clear_reference_cache(reference_type)
            return result
        return wrapper
    return decorator

