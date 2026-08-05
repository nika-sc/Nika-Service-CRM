"""
Утилиты для кэширования.
"""
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from typing import Callable, Any, Optional, Tuple
import hashlib
import json
import logging
from app.services.action_log_service import ActionLogService

logger = logging.getLogger(__name__)


def _json_default(obj: Any) -> Any:
    """Fallback encoder (prefer _to_json_safe before dumps)."""
    return _to_json_safe(obj)


def _to_json_safe(value: Any, *, _depth: int = 0) -> Any:
    """
    Рекурсивно приводит значение к JSON-совместимому виду.

    Один и тот же shape для Redis и in-memory: datetime/date → ISO str,
    Decimal → float, dict keys → str, модели с to_dict() → dict.
    """
    if _depth > 64:
        raise TypeError("cache value nesting too deep")

    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {
            str(k): _to_json_safe(v, _depth=_depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(v, _depth=_depth + 1) for v in value]
    if isinstance(value, set):
        return [_to_json_safe(v, _depth=_depth + 1) for v in value]

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _to_json_safe(to_dict(), _depth=_depth + 1)
        except Exception as exc:
            raise TypeError(
                f"to_dict() failed for {type(value).__name__}: {exc}"
            ) from exc

    raise TypeError(
        f"value of type {type(value).__name__} is not JSON-safe for cache "
        f"(do not cache model instances without to_dict)"
    )


def _prepare_cache_value(result: Any) -> Tuple[Optional[Any], bool]:
    """
    Returns (safe_value, ok). If ok is False, result must not be written to Redis
    (and should not be stored in memory as a divergent raw object).
    """
    try:
        return _to_json_safe(result), True
    except TypeError as exc:
        logger.warning("Skip Redis/memory cache normalize: %s", exc)
        return None, False


# Простое in-memory кэширование (можно заменить на Redis, Memcached и т.д.)
_cache = {}
_cache_timestamps = {}
_cache_access_times = {}  # Для LRU политики

# Максимальный размер кэша (по умолчанию 1000 записей)
MAX_CACHE_SIZE = 1000

# Redis опционально
_redis_client = None
try:
    import redis
    from app.config import Config
    redis_url = getattr(Config, 'REDIS_URL', None)
    if redis_url:
        _redis_client = redis.from_url(redis_url, decode_responses=True)
        logger.info("Redis подключен для кэширования")
except ImportError:
    logger.debug("Redis не установлен, используется in-memory кэш")
except Exception as e:
    logger.warning(f"Не удалось подключиться к Redis: {e}, используется in-memory кэш")


def _remove_from_cache(cache_key: str):
    """Удаляет запись из кэша и всех связанных словарей."""
    if cache_key in _cache:
        del _cache[cache_key]
    if cache_key in _cache_timestamps:
        del _cache_timestamps[cache_key]
    if cache_key in _cache_access_times:
        del _cache_access_times[cache_key]


def _evict_lru_entry():
    """Удаляет наименее недавно использованную запись (LRU)."""
    if not _cache_access_times:
        # Если нет записей о доступе, удаляем самую старую по времени создания
        if _cache_timestamps:
            oldest_key = min(_cache_timestamps.items(), key=lambda x: x[1])[0]
            _remove_from_cache(oldest_key)
            logger.debug(f"Evicted oldest entry: {oldest_key}")
        return
    
    # Находим ключ с наименьшим временем доступа
    lru_key = min(_cache_access_times.items(), key=lambda x: x[1])[0]
    _remove_from_cache(lru_key)
    logger.debug(f"Evicted LRU entry: {lru_key}")


def _generate_cache_key(func_name: str, key_prefix: str, args: tuple, kwargs: dict) -> str:
    """
    Генерирует ключ кэша.
    
    Args:
        func_name: Имя функции
        key_prefix: Префикс ключа
        args: Аргументы функции
        kwargs: Именованные аргументы функции
        
    Returns:
        Строка ключа кэша
    """
    # Создаем уникальный ключ из всех параметров
    key_data = {
        'func': func_name,
        'args': args,
        'kwargs': kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()
    
    return f"{key_prefix}:{key_hash}"


def cache_result(timeout: int = 300, key_prefix: str = 'cache') -> Callable:
    """
    Декоратор для кэширования результатов функций.
    
    Args:
        timeout: Время жизни кэша в секундах (по умолчанию 5 минут)
        key_prefix: Префикс для ключа кэша
        
    Usage:
        @cache_result(timeout=3600, key_prefix='device_types')
        def get_device_types():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            # Генерируем ключ кэша
            cache_key = _generate_cache_key(func.__name__, key_prefix, args, kwargs)
            current_time = time.time()
            
            # Проверяем кэш (Redis или in-memory)
            if _redis_client:
                try:
                    cached_data = _redis_client.get(cache_key)
                    if cached_data:
                        logger.debug(f"Cache hit (Redis): {cache_key}")
                        return json.loads(cached_data)
                except Exception as e:
                    logger.warning(f"Ошибка чтения из Redis: {e}")
            
            if cache_key in _cache:
                timestamp = _cache_timestamps.get(cache_key, 0)
                if current_time - timestamp < timeout:
                    logger.debug(f"Cache hit: {cache_key}")
                    # Обновляем время последнего доступа для LRU
                    _cache_access_times[cache_key] = current_time
                    return _cache[cache_key]
                else:
                    # Кэш устарел, удаляем
                    _remove_from_cache(cache_key)
            
            # Проверяем размер кэша перед добавлением новой записи
            if len(_cache) >= MAX_CACHE_SIZE:
                _evict_lru_entry()
            
            # Выполняем функцию
            logger.debug(f"Cache miss: {cache_key}")
            result = func(*args, **kwargs)

            safe, ok = _prepare_cache_value(result)
            if not ok:
                # Не кэшируем «сырые» модели — иначе Redis/memory разъедутся по типам
                return result

            if _redis_client:
                try:
                    _redis_client.setex(
                        cache_key,
                        timeout,
                        json.dumps(safe, ensure_ascii=False),
                    )
                    logger.debug(f"Cached in Redis: {cache_key}")
                except Exception as e:
                    logger.warning(f"Ошибка записи в Redis: {e}")

            _cache[cache_key] = safe
            _cache_timestamps[cache_key] = current_time
            _cache_access_times[cache_key] = current_time

            return safe
        return wrapper
    return decorator


def clear_cache(key_prefix: Optional[str] = None) -> int:
    """
    Очищает кэш.
    
    Args:
        key_prefix: Префикс для очистки (если None, очищает весь кэш)
        
    Returns:
        Количество удаленных записей
    """
    if key_prefix is None:
        count = len(_cache)
        _cache.clear()
        _cache_timestamps.clear()
        _cache_access_times.clear()
        logger.info(f"Cleared entire cache ({count} entries)")

        # Не трогаем весь Redis DB0: там же Socket.IO message_queue.
        # Префиксы приложения чистятся через clear_cache('dashboard_full') и т.п.

        # Логируем очистку всего кэша
        try:
            ActionLogService.log_action(
                user_id=None,  # Системная операция
                username='system',
                action_type='clear',
                entity_type='cache',
                entity_id=None,
                description="Очищен весь кэш системы",
                details={
                    'entries_cleared': count,
                    'key_prefix': None
                }
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать очистку кэша: {e}")

        return count
    
    # Удаляем только записи с указанным префиксом
    keys_to_delete = [k for k in _cache.keys() if k.startswith(f"{key_prefix}:")]
    for key in keys_to_delete:
        _remove_from_cache(key)

    redis_deleted = 0
    if _redis_client:
        try:
            redis_keys = list(_redis_client.scan_iter(match=f"{key_prefix}:*"))
            if redis_keys:
                redis_deleted = int(_redis_client.delete(*redis_keys))
        except Exception as e:
            logger.warning(f"Ошибка очистки Redis-кэша с префиксом {key_prefix}: {e}")

    deleted_count = len(keys_to_delete) + redis_deleted
    logger.info(f"Cleared cache with prefix '{key_prefix}' ({deleted_count} entries)")

    # Логируем очистку кэша с префиксом
    try:
        ActionLogService.log_action(
            user_id=None,  # Системная операция
            username='system',
            action_type='clear',
            entity_type='cache',
            entity_id=None,
            description=f"Очищен кэш с префиксом '{key_prefix}'",
            details={
                'entries_cleared': deleted_count,
                'key_prefix': key_prefix
            }
        )
    except Exception as e:
        logger.warning(f"Не удалось залогировать очистку кэша с префиксом {key_prefix}: {e}")

    return deleted_count


def get_cache_stats() -> dict:
    """
    Получает статистику кэша.
    
    Returns:
        Словарь со статистикой
    """
    import time
    
    total_entries = len(_cache)
    expired_entries = 0
    active_entries = 0
    
    current_time = time.time()
    for key, timestamp in _cache_timestamps.items():
        if current_time - timestamp > 300:  # 5 минут по умолчанию
            expired_entries += 1
        else:
            active_entries += 1
    
    # Группировка по префиксам
    prefix_stats = {}
    for key in _cache.keys():
        if ':' in key:
            prefix = key.split(':')[0]
            prefix_stats[prefix] = prefix_stats.get(prefix, 0) + 1
    
    return {
        'total_entries': total_entries,
        'expired_entries': expired_entries,
        'active_entries': active_entries,
        'by_prefix': prefix_stats
    }


def cleanup_expired_cache() -> int:
    """
    Очищает устаревшие записи из кэша.
    
    Returns:
        Количество удаленных записей
    """
    import time
    
    current_time = time.time()
    keys_to_delete = []
    
    # Находим устаревшие записи (старше 1 часа)
    for key, timestamp in _cache_timestamps.items():
        if current_time - timestamp > 3600:  # 1 час
            keys_to_delete.append(key)
    
    # Удаляем устаревшие записи
    for key in keys_to_delete:
        _remove_from_cache(key)
    
    if keys_to_delete:
        logger.info(f"Очищено {len(keys_to_delete)} устаревших записей из кэша")
    
    return len(keys_to_delete)
