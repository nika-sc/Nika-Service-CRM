"""
Модель закупки.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.base import BaseModel
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError
import sqlite3
import logging

logger = logging.getLogger(__name__)


class Purchase(BaseModel):
    """
    Модель закупки.
    
    Атрибуты:
        id: ID закупки
        supplier_id: ID поставщика (опционально)
        supplier_name: Название поставщика
        purchase_date: Дата закупки
        total_amount: Общая сумма
        status: Статус (draft, completed, cancelled)
        notes: Примечания
        created_by: ID пользователя, создавшего закупку
        created_at: Дата создания
        updated_at: Дата обновления
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.supplier_id = kwargs.get('supplier_id')
        self.supplier_name = kwargs.get('supplier_name', '')
        self.purchase_date = kwargs.get('purchase_date')
        self.total_amount = kwargs.get('total_amount', 0.0)
        self.status = kwargs.get('status', 'draft')
        self.notes = kwargs.get('notes')
        self.created_by = kwargs.get('created_by')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        
        # Связанные данные
        self.items = kwargs.get('items', [])
        self.created_by_username = kwargs.get('created_by_username')
        self.items_count = kwargs.get('items_count', 0)
    
    def validate(self) -> None:
        """
        Валидирует данные закупки.
        
        Raises:
            ValidationError: Если данные невалидны
        """
        errors = []
        
        if not self.supplier_name or not self.supplier_name.strip():
            errors.append("Название поставщика обязательно")
        
        if not self.purchase_date:
            errors.append("Дата закупки обязательна")
        
        if self.total_amount < 0:
            errors.append("Общая сумма не может быть отрицательной")
        
        if self.status not in ['draft', 'completed', 'cancelled']:
            errors.append("Неверный статус закупки")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    @classmethod
    def get_by_id(cls, purchase_id: int) -> Optional['Purchase']:
        """
        Получает закупку по ID.
        
        Args:
            purchase_id: ID закупки
            
        Returns:
            Purchase или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        p.*,
                        u.username AS created_by_username
                    FROM purchases AS p
                    LEFT JOIN users AS u ON u.id = p.created_by
                    WHERE p.id = ?
                ''', (purchase_id,))
                
                row = cursor.fetchone()
                if row:
                    purchase_dict = dict(row)
                    # Загружаем позиции
                    cursor.execute('''
                        SELECT * FROM purchase_items WHERE purchase_id = ?
                    ''', (purchase_id,))
                    items = [dict(row) for row in cursor.fetchall()]
                    purchase_dict['items'] = items
                    purchase_dict['items_count'] = len(items)
                    return cls.from_dict(purchase_dict)
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении закупки {purchase_id}: {e}")
            return None
    
    def save(self) -> 'Purchase':
        """
        Сохраняет закупку в БД.
        
        Returns:
            Purchase: Сохраненная заявка
        """
        self.validate()
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if self.id:
                    # Обновление
                    cursor.execute('''
                        UPDATE purchases 
                        SET supplier_name = ?,
                            purchase_date = ?,
                            total_amount = ?,
                            status = ?,
                            notes = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (
                        self.supplier_name,
                        self.purchase_date,
                        self.total_amount,
                        self.status,
                        self.notes,
                        self.id
                    ))
                else:
                    # Создание
                    cursor.execute('''
                        INSERT INTO purchases 
                        (supplier_name, purchase_date, total_amount, status, notes, created_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        self.supplier_name,
                        self.purchase_date,
                        self.total_amount,
                        self.status,
                        self.notes,
                        self.created_by
                    ))
                    self.id = cursor.lastrowid
                
                conn.commit()
                return self
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при сохранении закупки: {e}")
            raise ValidationError(f"Ошибка при сохранении закупки: {e}")
    
    def delete(self) -> bool:
        """
        Удаляет закупку из БД.
        
        Returns:
            True если успешно
        """
        if not self.id:
            return False
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM purchases WHERE id = ?', (self.id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении закупки {self.id}: {e}")
            return False

