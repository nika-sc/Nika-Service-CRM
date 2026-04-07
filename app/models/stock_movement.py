"""
Модель движения товара на складе.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.base import BaseModel
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError
import sqlite3
import logging

logger = logging.getLogger(__name__)


class StockMovement(BaseModel):
    """
    Модель движения товара на складе.
    
    Атрибуты:
        id: ID движения
        part_id: ID товара
        movement_type: Тип движения (purchase, sale, return, adjustment_increase, adjustment_decrease)
        quantity: Количество (положительное для прихода, отрицательное для расхода)
        reference_id: ID связанной сущности (purchase_id, order_id)
        reference_type: Тип связанной сущности (purchase, order, adjustment)
        created_by: ID пользователя
        notes: Примечания
        created_at: Дата создания
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.part_id = kwargs.get('part_id')
        self.movement_type = kwargs.get('movement_type', '')
        self.quantity = kwargs.get('quantity', 0)
        self.reference_id = kwargs.get('reference_id')
        self.reference_type = kwargs.get('reference_type')
        self.created_by = kwargs.get('created_by')
        self.notes = kwargs.get('notes')
        self.created_at = kwargs.get('created_at')
        
        # Связанные данные
        self.part_name = kwargs.get('part_name')
        self.part_number = kwargs.get('part_number')
        self.created_by_username = kwargs.get('created_by_username')
    
    def validate(self) -> None:
        """
        Валидирует данные движения.
        
        Raises:
            ValidationError: Если данные невалидны
        """
        errors = []
        
        if not self.part_id or self.part_id <= 0:
            errors.append("ID товара обязателен")
        
        if not self.movement_type:
            errors.append("Тип движения обязателен")
        
        valid_types = ['purchase', 'sale', 'return', 'adjustment_increase', 'adjustment_decrease']
        if self.movement_type not in valid_types:
            errors.append(f"Неверный тип движения. Допустимые: {', '.join(valid_types)}")
        
        if self.quantity == 0:
            errors.append("Количество не может быть нулевым")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    @classmethod
    def get_by_id(cls, movement_id: int) -> Optional['StockMovement']:
        """
        Получает движение по ID.
        
        Args:
            movement_id: ID движения
            
        Returns:
            StockMovement или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        sm.*,
                        p.name AS part_name,
                        p.part_number,
                        u.username AS created_by_username
                    FROM stock_movements AS sm
                    INNER JOIN parts AS p ON p.id = sm.part_id
                    LEFT JOIN users AS u ON u.id = sm.created_by
                    WHERE sm.id = ?
                ''', (movement_id,))
                
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении движения {movement_id}: {e}")
            return None
    
    def save(self) -> 'StockMovement':
        """
        Сохраняет движение в БД.
        
        Returns:
            StockMovement: Сохраненное движение
        """
        self.validate()
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO stock_movements 
                    (part_id, movement_type, quantity, reference_id, reference_type, created_by, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.part_id,
                    self.movement_type,
                    self.quantity,
                    self.reference_id,
                    self.reference_type,
                    self.created_by,
                    self.notes
                ))
                self.id = cursor.lastrowid
                
                conn.commit()
                return self
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при сохранении движения: {e}")
            raise ValidationError(f"Ошибка при сохранении движения: {e}")
    
    def delete(self) -> bool:
        """
        Удаляет движение из БД.
        
        Returns:
            True если успешно
        """
        if not self.id:
            return False
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM stock_movements WHERE id = ?', (self.id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении движения {self.id}: {e}")
            return False

