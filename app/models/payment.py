"""
Модель оплаты.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.base import BaseModel
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)


class Payment(BaseModel):
    """
    Модель оплаты.
    
    Атрибуты:
        id: ID оплаты
        order_id: ID заявки
        amount: Сумма оплаты
        payment_type: Тип оплаты (cash, card, transfer)
        payment_date: Дата оплаты
        created_by: ID пользователя, создавшего оплату
        created_by_username: Имя пользователя
        comment: Комментарий
        created_at: Дата создания записи
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.order_id = kwargs.get('order_id')
        self.amount = kwargs.get('amount', 0.0)
        self.payment_type = kwargs.get('payment_type', 'cash')
        self.payment_date = kwargs.get('payment_date')
        self.created_by = kwargs.get('created_by')
        self.created_by_username = kwargs.get('created_by_username')
        self.comment = kwargs.get('comment')
        self.created_at = kwargs.get('created_at')
    
    @classmethod
    def get_by_id(cls, payment_id: int) -> Optional['Payment']:
        """
        Получает оплату по ID.
        
        Args:
            payment_id: ID оплаты
            
        Returns:
            Payment или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,))
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении оплаты {payment_id}: {e}")
            return None
    
    @classmethod
    def get_by_order_id(cls, order_id: int) -> list['Payment']:
        """
        Получает все оплаты по заявке.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список оплат
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM payments 
                    WHERE order_id = ?
                    ORDER BY payment_date DESC, created_at DESC
                ''', (order_id,))
                rows = cursor.fetchall()
                return [cls.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении оплат заявки {order_id}: {e}")
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'amount': float(self.amount) if self.amount else 0.0,
            'payment_type': self.payment_type,
            'payment_date': self.payment_date,
            'created_by': self.created_by,
            'created_by_username': self.created_by_username,
            'comment': self.comment,
            'created_at': self.created_at
        }

