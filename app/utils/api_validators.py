"""
Утилиты для валидации API запросов.
Централизованная валидация входных данных для API endpoints.
"""
from typing import Any, Dict, List, Optional, Union
from flask import request
from app.utils.exceptions import ValidationError
from app.utils.validators import normalize_phone, validate_email
import logging

logger = logging.getLogger(__name__)


def validate_json_request() -> Dict[str, Any]:
    """
    Проверяет, что запрос содержит JSON и возвращает его.
    
    Returns:
        Dict с данными запроса
        
    Raises:
        ValidationError: Если запрос не содержит JSON
    """
    data = request.get_json(silent=True)
    if data is None:
        raise ValidationError("Запрос должен содержать JSON данные")
    return data


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Проверяет наличие обязательных полей в данных.
    
    Args:
        data: Словарь с данными
        required_fields: Список обязательных полей
        
    Raises:
        ValidationError: Если какое-то поле отсутствует
    """
    missing = [field for field in required_fields if not data.get(field)]
    if missing:
        raise ValidationError(f"Отсутствуют обязательные поля: {', '.join(missing)}")


def validate_phone_field(phone: Optional[str], field_name: str = 'phone', required: bool = True) -> Optional[str]:
    """
    Валидирует и нормализует номер телефона.
    
    Args:
        phone: Номер телефона
        field_name: Название поля для сообщения об ошибке
        required: Обязательно ли поле
        
    Returns:
        Нормализованный номер телефона или None
        
    Raises:
        ValidationError: Если телефон неверного формата
    """
    if not phone:
        if required:
            raise ValidationError(f"Поле '{field_name}' обязательно")
        return None
    
    phone = phone.strip()
    normalized = normalize_phone(phone)
    
    if not normalized or len(normalized) < 10:
        raise ValidationError(f"Неверный формат телефона в поле '{field_name}'")
    
    return normalized


def validate_email_field(email: Optional[str], field_name: str = 'email', required: bool = False) -> Optional[str]:
    """
    Валидирует email адрес.
    
    Args:
        email: Email адрес
        field_name: Название поля для сообщения об ошибке
        required: Обязательно ли поле
        
    Returns:
        Валидированный email или None
        
    Raises:
        ValidationError: Если email неверного формата
    """
    if not email:
        if required:
            raise ValidationError(f"Поле '{field_name}' обязательно")
        return None
    
    email = email.strip()
    if email:
        try:
            return validate_email(email)
        except ValidationError as e:
            raise ValidationError(f"Неверный формат email в поле '{field_name}': {e}")


def validate_integer_field(
    value: Any, 
    field_name: str, 
    required: bool = True,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None
) -> Optional[int]:
    """
    Валидирует целое число.
    
    Args:
        value: Значение для проверки
        field_name: Название поля
        required: Обязательно ли поле
        min_value: Минимальное значение
        max_value: Максимальное значение
        
    Returns:
        Валидированное целое число или None
        
    Raises:
        ValidationError: Если значение неверного формата или вне диапазона
    """
    if value is None or value == '':
        if required:
            raise ValidationError(f"Поле '{field_name}' обязательно")
        return None
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Поле '{field_name}' должно быть целым числом")
    
    if min_value is not None and int_value < min_value:
        raise ValidationError(f"Поле '{field_name}' должно быть не меньше {min_value}")
    
    if max_value is not None and int_value > max_value:
        raise ValidationError(f"Поле '{field_name}' должно быть не больше {max_value}")
    
    return int_value


def validate_float_field(
    value: Any,
    field_name: str,
    required: bool = True,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> Optional[float]:
    """
    Валидирует число с плавающей точкой.
    
    Args:
        value: Значение для проверки
        field_name: Название поля
        required: Обязательно ли поле
        min_value: Минимальное значение
        max_value: Максимальное значение
        
    Returns:
        Валидированное число или None
        
    Raises:
        ValidationError: Если значение неверного формата или вне диапазона
    """
    if value is None or value == '':
        if required:
            raise ValidationError(f"Поле '{field_name}' обязательно")
        return None
    
    try:
        float_value = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Поле '{field_name}' должно быть числом")
    
    if min_value is not None and float_value < min_value:
        raise ValidationError(f"Поле '{field_name}' должно быть не меньше {min_value}")
    
    if max_value is not None and float_value > max_value:
        raise ValidationError(f"Поле '{field_name}' должно быть не больше {max_value}")
    
    return float_value


def validate_string_field(
    value: Any,
    field_name: str,
    required: bool = True,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allowed_values: Optional[List[str]] = None
) -> Optional[str]:
    """
    Валидирует строковое поле.
    
    Args:
        value: Значение для проверки
        field_name: Название поля
        required: Обязательно ли поле
        min_length: Минимальная длина
        max_length: Максимальная длина
        allowed_values: Список допустимых значений
        
    Returns:
        Валидированная строка или None
        
    Raises:
        ValidationError: Если значение неверного формата
    """
    if value is None or value == '':
        if required:
            raise ValidationError(f"Поле '{field_name}' обязательно")
        return None
    
    str_value = str(value).strip()
    
    if min_length is not None and len(str_value) < min_length:
        raise ValidationError(f"Поле '{field_name}' должно быть не короче {min_length} символов")
    
    if max_length is not None and len(str_value) > max_length:
        raise ValidationError(f"Поле '{field_name}' должно быть не длиннее {max_length} символов")
    
    if allowed_values is not None and str_value not in allowed_values:
        raise ValidationError(f"Поле '{field_name}' должно быть одним из: {', '.join(allowed_values)}")
    
    return str_value


def validate_list_field(
    value: Any,
    field_name: str,
    required: bool = True,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    item_validator: Optional[callable] = None
) -> Optional[List]:
    """
    Валидирует список.
    
    Args:
        value: Значение для проверки
        field_name: Название поля
        required: Обязательно ли поле
        min_items: Минимальное количество элементов
        max_items: Максимальное количество элементов
        item_validator: Функция для валидации каждого элемента
        
    Returns:
        Валидированный список или None
        
    Raises:
        ValidationError: Если значение неверного формата
    """
    if value is None:
        if required:
            raise ValidationError(f"Поле '{field_name}' обязательно")
        return None
    
    if not isinstance(value, list):
        raise ValidationError(f"Поле '{field_name}' должно быть списком")
    
    if min_items is not None and len(value) < min_items:
        raise ValidationError(f"Поле '{field_name}' должно содержать не менее {min_items} элементов")
    
    if max_items is not None and len(value) > max_items:
        raise ValidationError(f"Поле '{field_name}' должно содержать не более {max_items} элементов")
    
    if item_validator:
        for i, item in enumerate(value):
            try:
                item_validator(item, f"{field_name}[{i}]")
            except ValidationError as e:
                raise ValidationError(f"Ошибка в элементе {i} поля '{field_name}': {e}")
    
    return value
