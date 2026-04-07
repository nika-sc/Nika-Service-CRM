"""
Типы данных для типизации.

Определяет TypedDict и другие типы для использования в сервисах и моделях.
"""
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime


class CustomerDict(TypedDict, total=False):
    """Словарь с данными клиента."""
    id: int
    name: str
    phone: str
    email: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class DeviceDict(TypedDict, total=False):
    """Словарь с данными устройства."""
    id: int
    customer_id: int
    device_type_id: int
    device_brand_id: int
    serial_number: Optional[str]
    created_at: Optional[str]
    device_type_name: Optional[str]
    device_brand_name: Optional[str]


class OrderDict(TypedDict, total=False):
    """Словарь с данными заявки."""
    id: int
    order_id: str
    device_id: int
    customer_id: int
    manager_id: int
    master_id: Optional[int]
    status_id: Optional[int]
    status: str
    prepayment: str
    password: Optional[str]
    appearance: Optional[str]
    comment: Optional[str]
    symptom_tags: Optional[str]
    hidden: int
    created_at: Optional[str]
    updated_at: Optional[str]
    # Связанные данные
    customer_name: Optional[str]
    customer_phone: Optional[str]
    device_type_name: Optional[str]
    device_brand_name: Optional[str]
    manager_name: Optional[str]
    master_name: Optional[str]
    status_name: Optional[str]
    status_color: Optional[str]


class OrderTotalsDict(TypedDict):
    """Словарь с суммами по заявке."""
    services_total: float
    parts_total: float
    payments_total: float
    debt: float


class PaymentDict(TypedDict, total=False):
    """Словарь с данными оплаты."""
    id: int
    order_id: int
    amount: float
    payment_type: str
    payment_date: Optional[str]
    created_by: Optional[int]
    created_by_username: Optional[str]
    comment: Optional[str]
    created_at: Optional[str]


class CommentDict(TypedDict, total=False):
    """Словарь с данными комментария."""
    id: int
    order_id: int
    author_name: str
    comment_text: str
    created_at: Optional[str]


class ServiceDict(TypedDict, total=False):
    """Словарь с данными услуги."""
    id: int
    name: str
    price: float
    is_default: int
    sort_order: int
    created_at: Optional[str]
    updated_at: Optional[str]


class PartDict(TypedDict, total=False):
    """Словарь с данными запчасти."""
    id: int
    name: str
    part_number: Optional[str]
    description: Optional[str]
    retail_price: float
    purchase_price: Optional[float]
    stock_quantity: int
    min_quantity: int
    category: Optional[str]
    supplier: Optional[str]
    unit: Optional[str]
    warranty_days: Optional[int]
    is_deleted: int
    comment: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class ReferenceDict(TypedDict, total=False):
    """Словарь с данными справочника."""
    id: int
    name: str
    sort_order: Optional[int]
    created_at: Optional[str]
    # Для статусов
    code: Optional[str]
    color: Optional[str]
    is_default: Optional[int]


class OrderFiltersDict(TypedDict, total=False):
    """Словарь с фильтрами для поиска заявок."""
    status: Optional[str]
    status_id: Optional[int]
    customer_id: Optional[int]
    device_id: Optional[int]
    manager_id: Optional[int]
    master_id: Optional[int]
    search: Optional[str]
    date_from: Optional[str]
    date_to: Optional[str]
    hidden: Optional[int]


class PaginationResult(TypedDict):
    """Результат пагинации."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    pages: int

