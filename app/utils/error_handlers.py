"""
Централизованная обработка ошибок.

Содержит обработчики ошибок для Flask и декораторы для сервисов.
"""
from functools import wraps
from typing import Callable, Any, Optional
from flask import jsonify, render_template, request, flash, redirect, url_for
from flask_login import current_user
import logging
import traceback

from app.utils.exceptions import (
    BaseAppException,
    ValidationError,
    NotFoundError,
    PermissionError,
    DatabaseError
)
from flask_wtf.csrf import CSRFError

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """
    Регистрирует обработчики ошибок для Flask приложения.
    
    Args:
        app: Экземпляр Flask приложения
    """
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """Обработчик ошибок валидации."""
        from flask import has_request_context
        logger.warning(f"Ошибка валидации: {error}")
        
        # Если это AJAX запрос, возвращаем JSON
        if has_request_context() and (request.is_json or request.path.startswith('/api/')):
            return jsonify({
                'success': False,
                'error': str(error),
                'error_type': 'validation'
            }), 400
        
        # Иначе показываем flash сообщение
        flash(str(error), 'error')
        referrer = request.referrer if has_request_context() else None
        return redirect(referrer or url_for('main.home')), 400
    
    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error: NotFoundError):
        """Обработчик ошибок 'не найдено'."""
        from flask import has_request_context
        logger.warning(f"Ресурс не найден: {error}")
        
        # Если это AJAX запрос, возвращаем JSON
        if has_request_context() and (request.is_json or request.path.startswith('/api/')):
            return jsonify({
                'success': False,
                'error': str(error),
                'error_type': 'not_found'
            }), 404
        
        # Иначе показываем flash сообщение
        flash(str(error), 'error')
        referrer = request.referrer if has_request_context() else None
        return redirect(referrer or url_for('main.home')), 404
    
    @app.errorhandler(PermissionError)
    def handle_permission_error(error: PermissionError):
        """Обработчик ошибок доступа."""
        from flask import has_request_context
        logger.warning(f"Ошибка доступа: {error}")
        
        # Если это AJAX запрос, возвращаем JSON
        if has_request_context() and (request.is_json or request.path.startswith('/api/')):
            return jsonify({
                'success': False,
                'error': str(error),
                'error_type': 'permission'
            }), 403
        
        # Иначе показываем flash сообщение
        flash(str(error), 'error')
        referrer = request.referrer if has_request_context() else None
        return redirect(referrer or url_for('main.home')), 403
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(error: DatabaseError):
        """Обработчик ошибок базы данных."""
        from flask import has_request_context
        logger.error(f"Ошибка базы данных: {error}", exc_info=True)
        
        # Если это AJAX запрос, возвращаем JSON
        if has_request_context() and (request.is_json or request.path.startswith('/api/')):
            return jsonify({
                'success': False,
                'error': 'Ошибка базы данных. Пожалуйста, попробуйте позже.',
                'error_type': 'database'
            }), 500
        
        # Иначе показываем flash сообщение
        flash('Произошла ошибка базы данных. Пожалуйста, попробуйте позже.', 'error')
        referrer = request.referrer if has_request_context() else None
        return redirect(referrer or url_for('main.home')), 500
    
    @app.errorhandler(BaseAppException)
    def handle_base_app_error(error: BaseAppException):
        """Обработчик базовых ошибок приложения."""
        from flask import has_request_context
        logger.error(f"Ошибка приложения: {error}", exc_info=True)
        
        # Если это AJAX запрос, возвращаем JSON
        if has_request_context() and (request.is_json or request.path.startswith('/api/')):
            return jsonify({
                'success': False,
                'error': str(error),
                'error_type': 'application'
            }), 500
        
        # Иначе показываем flash сообщение
        flash(str(error), 'error')
        referrer = request.referrer if has_request_context() else None
        return redirect(referrer or url_for('main.home')), 500
    
    @app.errorhandler(404)
    def handle_404(error):
        """Обработчик 404 ошибок."""
        from flask import has_request_context
        path = request.path if has_request_context() else 'unknown'
        logger.warning(f"Страница не найдена: {path}")
        
        if has_request_context() and (request.is_json or request.path.startswith('/api/')):
            return jsonify({
                'success': False,
                'error': 'Страница не найдена',
                'error_type': 'not_found'
            }), 404
        
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def handle_500(error):
        """Обработчик 500 ошибок."""
        from flask import has_request_context
        logger.error(f"Внутренняя ошибка сервера: {error}", exc_info=True)
        
        if has_request_context() and (request.is_json or request.path.startswith('/api/')):
            return jsonify({
                'success': False,
                'error': 'Внутренняя ошибка сервера. Пожалуйста, попробуйте позже.',
                'error_type': 'internal_server_error'
            }), 500
        
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """Обработчик ошибок CSRF."""
        from flask import has_request_context
        logger.warning(f"CSRF ошибка: {error}")
        
        # Если это API запрос, возвращаем JSON
        if has_request_context() and (request.is_json or request.path.startswith('/api/')):
            return jsonify({
                'success': False,
                'error': 'Ошибка CSRF токена. Пожалуйста, обновите страницу и попробуйте снова.',
                'error_type': 'csrf_error'
            }), 400
        
        # Иначе показываем flash сообщение
        flash('Ошибка безопасности. Пожалуйста, обновите страницу и попробуйте снова.', 'error')
        referrer = request.referrer if has_request_context() else None
        return redirect(referrer or url_for('main.home')), 400


def handle_service_error(func: Callable) -> Callable:
    """
    Декоратор для обработки ошибок в сервисах.
    
    Логирует ошибки и преобразует их в соответствующие исключения приложения.
    
    Args:
        func: Функция сервиса
        
    Returns:
        Обернутая функция с обработкой ошибок
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValidationError, NotFoundError, PermissionError, DatabaseError):
            # Пробрасываем наши исключения дальше
            raise
        except Exception as e:
            # Логируем неожиданные ошибки
            logger.exception(f"Неожиданная ошибка в {func.__name__}: {e}")
            raise DatabaseError(f"Произошла ошибка при выполнении операции: {e}")
    
    return wrapper


def log_error(error: Exception, context: str = "", user_id: Optional[int] = None):
    """
    Логирует ошибку с контекстом.
    
    Args:
        error: Исключение
        context: Контекст, в котором произошла ошибка
        user_id: ID пользователя (если доступен)
    """
    user_info = f"User ID: {user_id}" if user_id else "Anonymous"
    context_info = f"Context: {context}" if context else ""
    
    logger.error(
        f"Ошибка: {error}\n{user_info}\n{context_info}\n{traceback.format_exc()}",
        exc_info=True
    )


def format_error_message(error: Exception, default_message: str = "Произошла ошибка") -> str:
    """
    Форматирует сообщение об ошибке для пользователя.
    
    Args:
        error: Исключение
        default_message: Сообщение по умолчанию
        
    Returns:
        Отформатированное сообщение об ошибке
    """
    if isinstance(error, ValidationError):
        return str(error)
    elif isinstance(error, NotFoundError):
        return str(error)
    elif isinstance(error, PermissionError):
        return "У вас нет прав для выполнения этого действия"
    elif isinstance(error, DatabaseError):
        return "Ошибка базы данных. Пожалуйста, попробуйте позже."
    else:
        return default_message
