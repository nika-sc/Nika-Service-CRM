"""
Модуль для оптимизированных SQL-запросов.
"""
from .order_queries import OrderQueries
from .customer_queries import CustomerQueries
from .device_queries import DeviceQueries
from .reference_queries import ReferenceQueries
from .payment_queries import PaymentQueries
from .comment_queries import CommentQueries
from .warehouse_queries import WarehouseQueries

__all__ = [
    'OrderQueries',
    'CustomerQueries',
    'DeviceQueries',
    'ReferenceQueries',
    'PaymentQueries',
    'CommentQueries',
    'WarehouseQueries'
]
