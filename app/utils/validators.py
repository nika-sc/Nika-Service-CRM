"""
Валидаторы для проверки данных.
"""
from typing import Any, Dict, List, Optional
import re
import logging
from app.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


def normalize_phone(phone: str) -> str:
    """
    Нормализует номер телефона (без валидации).
    
    Args:
        phone: Номер телефона
        
    Returns:
        Нормализованный номер телефона (только цифры, начинается с 7)
    """
    if not phone:
        return ""
    
    # Удаляем все нецифровые символы
    digits = re.sub(r'\D', '', phone)
    
    # Если начинается с 8, заменяем на 7
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    
    # Если не начинается с 7 и есть цифры, добавляем 7
    if digits and not digits.startswith('7'):
        digits = '7' + digits
    
    return digits


def validate_phone(phone: str) -> str:
    """
    Валидирует и нормализует номер телефона.
    
    Args:
        phone: Номер телефона
        
    Returns:
        Нормализованный номер телефона
        
    Raises:
        ValidationError: Если номер невалидный
    """
    if not phone:
        raise ValidationError("Номер телефона не может быть пустым")
    
    # Используем normalize_phone для нормализации
    digits = normalize_phone(phone)
    
    # Проверяем длину (минимум 10 цифр)
    if len(digits) < 10:
        raise ValidationError("Номер телефона должен содержать минимум 10 цифр")
    
    return digits


def validate_email(email: str) -> str:
    """
    Валидирует email адрес.
    
    Args:
        email: Email адрес
        
    Returns:
        Валидированный email
        
    Raises:
        ValidationError: Если email невалидный
    """
    if not email:
        return ""  # Email опционален
    
    email = email.strip().lower()
    
    # Простая проверка формата
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Неверный формат email адреса")
    
    return email


def validate_order_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидирует данные заявки.
    
    Args:
        data: Словарь с данными заявки
        
    Returns:
        Валидированные данные
        
    Raises:
        ValidationError: Если данные невалидны
    """
    errors = []
    
    # Проверка обязательных полей
    if 'customer_id' not in data or not data['customer_id']:
        errors.append("Не указан клиент")
    
    if 'device_id' not in data or not data['device_id']:
        errors.append("Не указано устройство")
    
    if 'manager_id' not in data or not data['manager_id']:
        errors.append("Не указан менеджер")
    
    # Валидация сумм
    if 'prepayment' in data:
        try:
            prepayment = float(data['prepayment'])
            if prepayment < 0:
                errors.append("Предоплата не может быть отрицательной")
        except (ValueError, TypeError):
            errors.append("Неверный формат предоплаты")
    
    if errors:
        raise ValidationError("; ".join(errors))
    
    return data


def validate_customer_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидирует данные клиента.
    
    Args:
        data: Словарь с данными клиента
        
    Returns:
        Валидированные данные
        
    Raises:
        ValidationError: Если данные невалидны
    """
    errors = []
    
    # Проверка имени
    if 'name' not in data or not data['name'] or not data['name'].strip():
        errors.append("Имя клиента не может быть пустым")
    
    # Валидация телефона
    if 'phone' in data and data['phone']:
        try:
            data['phone'] = validate_phone(data['phone'])
        except ValidationError as e:
            errors.append(str(e))
    else:
        errors.append("Номер телефона обязателен")
    
    # Валидация email (если указан)
    if 'email' in data and data['email']:
        try:
            data['email'] = validate_email(data['email'])
        except ValidationError as e:
            errors.append(str(e))
    
    if errors:
        raise ValidationError("; ".join(errors))
    
    return data


def validate_price(price: Any) -> float:
    """
    Валидирует цену.
    
    Args:
        price: Цена
        
    Returns:
        Валидированная цена
        
    Raises:
        ValidationError: Если цена невалидна
    """
    try:
        price = float(price)
        if price < 0:
            raise ValidationError("Цена не может быть отрицательной")
        return round(price, 2)
    except (ValueError, TypeError):
        raise ValidationError("Неверный формат цены")


def validate_quantity(quantity: Any) -> int:
    """
    Валидирует количество.
    
    Args:
        quantity: Количество
        
    Returns:
        Валидированное количество
        
    Raises:
        ValidationError: Если количество невалидно
    """
    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValidationError("Количество должно быть больше нуля")
        return quantity
    except (ValueError, TypeError):
        raise ValidationError("Неверный формат количества")
