"""
Модель запчасти.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.base import BaseModel
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)


class Part(BaseModel):
    """
    Модель запчасти.
    
    Атрибуты:
        id: ID запчасти
        name: Название запчасти
        part_number: Артикул
        description: Описание
        retail_price: Розничная цена
        purchase_price: Закупочная цена
        stock_quantity: Количество на складе
        min_quantity: Минимальное количество
        category: Категория
        supplier: Поставщик
        unit: Единица измерения
        warranty_days: Гарантия в днях
        is_deleted: Мягкое удаление (0 - не удален, 1 - удален)
        comment: Комментарий
        created_at: Дата создания
        updated_at: Дата обновления
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.name = kwargs.get('name', '')
        self.part_number = kwargs.get('part_number')
        self.description = kwargs.get('description')
        # Поддержка старого поля price для обратной совместимости
        self.retail_price = kwargs.get('retail_price') or kwargs.get('price', 0.0)
        self.purchase_price = kwargs.get('purchase_price', 0.0)
        self.stock_quantity = kwargs.get('stock_quantity', 0)
        self.min_quantity = kwargs.get('min_quantity', 0)
        self.category = kwargs.get('category')
        self.supplier = kwargs.get('supplier')
        self.unit = kwargs.get('unit', 'шт')
        self.warranty_days = kwargs.get('warranty_days')
        self.is_deleted = kwargs.get('is_deleted', 0)
        self.comment = kwargs.get('comment')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
    
    @classmethod
    def get_by_id(cls, part_id: int, include_deleted: bool = False) -> Optional['Part']:
        """
        Получает запчасть по ID.
        
        Args:
            part_id: ID запчасти
            include_deleted: Включать удаленные товары
            
        Returns:
            Part или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                if include_deleted:
                    cursor.execute('SELECT * FROM parts WHERE id = ?', (part_id,))
                else:
                    cursor.execute('SELECT * FROM parts WHERE id = ? AND is_deleted = 0', (part_id,))
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении запчасти {part_id}: {e}")
            return None
    
    @classmethod
    def get_all(cls, category: str = None) -> list['Part']:
        """
        Получает все запчасти, опционально отфильтрованные по категории.
        
        Args:
            category: Категория для фильтрации (опционально)
            
        Returns:
            Список запчастей
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                if category:
                    cursor.execute('''
                        SELECT * FROM parts 
                        WHERE category = ? AND is_deleted = 0
                        ORDER BY name
                    ''', (category,))
                else:
                    cursor.execute('''
                        SELECT * FROM parts 
                        WHERE is_deleted = 0
                        ORDER BY name
                    ''')
                rows = cursor.fetchall()
                return [cls.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении запчастей: {e}")
            return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        return {
            'id': self.id,
            'name': self.name,
            'part_number': self.part_number,
            'description': self.description,
            'retail_price': float(self.retail_price) if self.retail_price else 0.0,
            'purchase_price': float(self.purchase_price) if self.purchase_price else 0.0,
            'stock_quantity': self.stock_quantity,
            'min_quantity': self.min_quantity,
            'category': self.category,
            'supplier': self.supplier,
            'unit': self.unit,
            'warranty_days': self.warranty_days,
            'is_deleted': self.is_deleted,
            'comment': self.comment,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

