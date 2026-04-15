"""
Утилиты для мониторинга производительности.
"""
import time
import logging
import functools
from typing import Callable, Any, Optional
from flask import request, g

logger = logging.getLogger(__name__)

# Порог для медленных запросов (в секундах)
SLOW_QUERY_THRESHOLD = 1.0
SLOW_SERVICE_THRESHOLD = 0.5


def monitor_performance(threshold: float = SLOW_SERVICE_THRESHOLD, log_args: bool = False):
    """
    Декоратор для мониторинга производительности функций.
    
    Args:
        threshold: Порог времени выполнения в секундах (по умолчанию 0.5)
        log_args: Логировать аргументы функции (по умолчанию False)
    
    Usage:
        @monitor_performance(threshold=1.0)
        def my_slow_function():
            # ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                if elapsed > threshold:
                    log_msg = f"Медленный запрос: {func_name} выполнялся {elapsed:.3f}с"
                    
                    if log_args and (args or kwargs):
                        # Логируем аргументы (осторожно с чувствительными данными)
                        safe_args = []
                        for arg in args[:3]:  # Первые 3 аргумента
                            if isinstance(arg, (str, int, float, bool)):
                                safe_args.append(str(arg)[:50])  # Ограничиваем длину
                        if safe_args:
                            log_msg += f" (args: {', '.join(safe_args)})"
                    
                    logger.warning(log_msg)
                elif elapsed > threshold * 0.7:  # Предупреждение при 70% от порога
                    logger.debug(f"{func_name} выполнялся {elapsed:.3f}с")
                
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"Ошибка в {func_name} после {elapsed:.3f}с: {e}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


def monitor_db_query(threshold: float = SLOW_QUERY_THRESHOLD):
    """
    Декоратор для мониторинга производительности SQL запросов.
    
    Args:
        threshold: Порог времени выполнения в секундах (по умолчанию 1.0)
    
    Usage:
        @monitor_db_query(threshold=0.5)
        def get_orders_with_details():
            # ...
    """
    return monitor_performance(threshold=threshold, log_args=False)


def log_slow_request(threshold: float = SLOW_QUERY_THRESHOLD):
    """
    Декоратор для Flask routes для логирования медленных HTTP запросов.
    
    Args:
        threshold: Порог времени выполнения в секундах (по умолчанию 1.0)
    
    Usage:
        @bp.route('/orders')
        @login_required
        @log_slow_request(threshold=2.0)
        def orders():
            # ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                if elapsed > threshold:
                    path = request.path if hasattr(request, 'path') else 'unknown'
                    method = request.method if hasattr(request, 'method') else 'unknown'
                    logger.warning(
                        f"Медленный HTTP запрос: {method} {path} "
                        f"выполнялся {elapsed:.3f}с"
                    )
                
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                path = request.path if hasattr(request, 'path') else 'unknown'
                logger.error(
                    f"Ошибка в HTTP запросе {path} после {elapsed:.3f}с: {e}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


class PerformanceTimer:
    """
    Context manager для измерения времени выполнения блока кода.
    
    Usage:
        with PerformanceTimer("my_operation"):
            # код
    """
    
    def __init__(self, operation_name: str, threshold: Optional[float] = None):
        """
        Args:
            operation_name: Название операции для логирования
            threshold: Порог времени выполнения (опционально)
        """
        self.operation_name = operation_name
        self.threshold = threshold or SLOW_SERVICE_THRESHOLD
        self.start_time = None
        self.elapsed = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        
        if exc_type is None:
            if self.elapsed > self.threshold:
                logger.warning(
                    f"Медленная операция: {self.operation_name} "
                    f"выполнялась {self.elapsed:.3f}с"
                )
            else:
                logger.debug(
                    f"Операция {self.operation_name} выполнена за {self.elapsed:.3f}с"
                )
        else:
            logger.error(
                f"Ошибка в операции {self.operation_name} "
                f"после {self.elapsed:.3f}с: {exc_val}",
                exc_info=True
            )
        
        return False  # Не подавляем исключения
    
    def get_elapsed(self) -> float:
        """Возвращает время выполнения в секундах."""
        if self.elapsed is None:
            return time.time() - self.start_time
        return self.elapsed
