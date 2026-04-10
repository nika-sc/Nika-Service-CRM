"""
Сервисы приложения.
"""
from .order_service import OrderService
from .customer_service import CustomerService
from .device_service import DeviceService
from .reference_service import ReferenceService
from .payment_service import PaymentService
from .comment_service import CommentService
from .user_service import UserService
from .settings_service import SettingsService
from .warehouse_service import WarehouseService
from .reports_service import ReportsService

__all__ = [
    'OrderService',
    'CustomerService',
    'DeviceService',
    'ReferenceService',
    'PaymentService',
    'CommentService',
    'UserService',
    'SettingsService',
    'WarehouseService',
    'ReportsService'
]
