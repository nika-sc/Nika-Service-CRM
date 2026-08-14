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

    Принимает российские номера с +7, 7 или 8 в начале, с пробелами/скобками,
    и случай «+7» + вставка номера, который уже начинается с 7/8.

    Returns:
        Только цифры, для РФ обычно 11 знаков начиная с 7.
    """
    if not phone:
        return ""

    digits = re.sub(r"\D", "", str(phone))
    if digits.startswith("00"):
        digits = digits[2:]
    if not digits:
        return ""

    # +7 / 8, затем вставили номер, который уже с 7 или 8 (12 цифр, дальше мобильный 9…)
    if (
        len(digits) == 12
        and digits[0] in "78"
        and digits[1] in "78"
        and digits[2] == "9"
    ):
        digits = "7" + digits[2:]

    if digits.startswith("8"):
        digits = "7" + digits[1:]

    if digits and not digits.startswith("7"):
        digits = "7" + digits

    return digits


def phone_lookup_variants(phone: str) -> list:
    """Варианты записи одного РФ-номера для поиска в БД (7 / 8 / +7 / 10 цифр)."""
    raw = (phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    normalized = normalize_phone(raw)
    seen = []
    for item in (
        raw,
        digits,
        normalized,
    ):
        if item and item not in seen:
            seen.append(item)
    if normalized.startswith("7") and len(normalized) >= 11:
        rest = normalized[1:]
        extra = [
            "8" + rest,
            rest,
            "+" + normalized,
            "+7" + rest,
            f"+7({rest[0:3]}){rest[3:6]}-{rest[6:8]}-{rest[8:10]}",
            f"+7 ({rest[0:3]}) {rest[3:6]}-{rest[6:8]}-{rest[8:10]}",
            f"8 ({rest[0:3]}) {rest[3:6]}-{rest[6:8]}-{rest[8:10]}",
        ]
        for item in extra:
            if item and item not in seen:
                seen.append(item)
    return seen


PASSWORD_MIN_LEN = 6
PASSWORD_MAX_LEN = 256


def password_meets_policy(password: str) -> bool:
    """True if password length is allowed for create/change (server-side, not HTML)."""
    n = len(password or "")
    return PASSWORD_MIN_LEN <= n <= PASSWORD_MAX_LEN


def validate_new_password(password: str) -> str:
    """
    Проверка нового пароля на сервере (создание / смена).
    HTML minlength не граница.
    """
    n = len(password or "")
    if n < PASSWORD_MIN_LEN:
        raise ValidationError("Пароль должен быть не менее 6 символов")
    if n > PASSWORD_MAX_LEN:
        raise ValidationError("Пароль слишком длинный")
    return password


def password_eligible_for_verify(password: str) -> bool:
    """Вход: не хешировать пустой или слишком длинный пароль."""
    n = len(password or "")
    return 1 <= n <= PASSWORD_MAX_LEN


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


def parse_non_negative_money(raw: Any, field_label: str = "Сумма") -> float:
    """
    Парсит неотрицательную денежную сумму из формы.

    Допускает пустое значение (=0) и десятичную запятую (`1,5` → 1.5).
    """
    text = '' if raw is None else str(raw).strip()
    if not text:
        return 0.0
    # Одна запятая как десятичный разделитель (RU-ввод), иначе оставляем как есть.
    if text.count(',') == 1 and '.' not in text:
        text = text.replace(',', '.', 1)
    try:
        value = float(text)
    except (ValueError, TypeError):
        raise ValidationError(f"Неверный формат: {field_label}")
    if value < 0:
        raise ValidationError(f"{field_label} не может быть отрицательной")
    return value


def money_values_equal(left: Any, right: Any) -> bool:
    """Сравнение денежных значений с учётом '100' vs '100.0'."""
    try:
        return abs(float(left or 0) - float(right or 0)) < 1e-9
    except (ValueError, TypeError):
        return str(left or '') == str(right or '')


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
