"""
Кастомные исключения приложения.
"""


class BaseAppException(Exception):
    """Базовое исключение приложения."""
    pass


class ValidationError(BaseAppException):
    """Ошибка валидации данных."""
    pass


class NotFoundError(BaseAppException):
    """Ресурс не найден."""
    pass


class PermissionError(BaseAppException):
    """Ошибка доступа."""
    pass


class DatabaseError(BaseAppException):
    """Ошибка базы данных."""
    pass

