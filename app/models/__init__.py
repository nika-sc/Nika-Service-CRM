"""
Модели данных.
"""
from app.models.base import BaseModel
from app.models.customer import Customer
from app.models.device import Device
from app.models.order import Order
from app.models.service import Service
from app.models.part import Part
from app.models.payment import Payment
from app.models.user import User
from app.models.purchase import Purchase
from app.models.stock_movement import StockMovement

__all__ = [
    'BaseModel',
    'Customer',
    'Device',
    'Order',
    'Service',
    'Part',
    'Payment',
    'User',
    'Purchase',
    'StockMovement'
]
