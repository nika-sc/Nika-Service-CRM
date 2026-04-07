"""
Модель услуги.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.base import BaseModel
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)


class Service(BaseModel):
    """
    Модель услуги.
    
    Атрибуты:
        id: ID услуги
        name: Название услуги
        price: Цена услуги
        is_default: Является ли услугой по умолчанию
        sort_order: Порядок сортировки
        created_at: Дата создания
        updated_at: Дата обновления
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.name = kwargs.get('name', '')
        self.price = kwargs.get('price', 0.0)
        self.is_default = kwargs.get('is_default', 0)
        self.sort_order = kwargs.get('sort_order', 0)
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
    
    @classmethod
    def get_by_id(cls, service_id: int) -> Optional['Service']:
        """
        Получает услугу по ID.
        
        Args:
            service_id: ID услуги
            
        Returns:
            Service или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении услуги {service_id}: {e}")
            return None
    
    @classmethod
    def get_all(cls) -> list['Service']:
        """
        Получает все услуги, отсортированные по sort_order.
        
        Returns:
            Список услуг
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM services 
                    ORDER BY sort_order, id
                ''')
                rows = cursor.fetchall()
                return [cls.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении услуг: {e}")
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        return {
            'id': self.id,
            'name': self.name,
            'price': float(self.price) if self.price else 0.0,
            'is_default': bool(self.is_default) if self.is_default else False,
            'sort_order': self.sort_order,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

