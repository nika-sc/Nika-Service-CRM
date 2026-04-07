"""
Модель устройства.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.base import BaseModel
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError
import sqlite3
import logging

logger = logging.getLogger(__name__)


class Device(BaseModel):
    """
    Модель устройства.
    
    Атрибуты:
        id: ID устройства
        customer_id: ID клиента
        device_type_id: ID типа устройства
        device_brand_id: ID бренда устройства
        serial_number: Серийный номер
        created_at: Дата создания
        device_type: Название типа устройства (вычисляемое)
        device_brand: Название бренда (вычисляемое)
        customer_name: Имя клиента (вычисляемое)
        customer_phone: Телефон клиента (вычисляемое)
        customer_email: Email клиента (вычисляемое)
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.customer_id = kwargs.get('customer_id')
        self.device_type_id = kwargs.get('device_type_id')
        self.device_brand_id = kwargs.get('device_brand_id')
        self.serial_number = kwargs.get('serial_number')
        self.password = kwargs.get('password')
        self.symptom_tags = kwargs.get('symptom_tags')
        self.appearance_tags = kwargs.get('appearance_tags')
        self.comment = kwargs.get('comment')
        self.created_at = kwargs.get('created_at')
        self.device_type = kwargs.get('device_type')
        self.device_brand = kwargs.get('device_brand')
        self.customer_name = kwargs.get('customer_name')
        self.customer_phone = kwargs.get('customer_phone')
        self.customer_email = kwargs.get('customer_email')
    
    @classmethod
    def get_by_id(cls, device_id: int) -> Optional['Device']:
        """
        Получает устройство по ID.
        
        Args:
            device_id: ID устройства
            
        Returns:
            Device или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        d.id,
                        d.serial_number,
                        d.device_type_id,
                        d.device_brand_id,
                        d.customer_id,
                        d.password,
                        d.symptom_tags,
                        d.appearance_tags,
                        d.comment,
                        dt.name AS device_type,
                        db.name AS device_brand,
                        d.created_at,
                        c.name AS customer_name,
                        c.phone AS customer_phone,
                        c.email AS customer_email
                    FROM devices AS d
                    LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                    LEFT JOIN customers AS c ON c.id = d.customer_id
                    WHERE d.id = ?
                ''', (device_id,))
                
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении устройства {device_id}: {e}")
            return None
    
    @classmethod
    def get_by_customer_id(cls, customer_id: int) -> List['Device']:
        """
        Получает все устройства клиента.
        
        Args:
            customer_id: ID клиента
            
        Returns:
            Список устройств
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        d.id,
                        d.serial_number,
                        d.device_type_id,
                        d.device_brand_id,
                        d.customer_id,
                        d.password,
                        d.symptom_tags,
                        d.appearance_tags,
                        d.comment,
                        dt.name AS device_type,
                        db.name AS device_brand,
                        d.created_at
                    FROM devices AS d
                    LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                    WHERE d.customer_id = ?
                    ORDER BY d.created_at DESC
                ''', (customer_id,))
                
                rows = cursor.fetchall()
                return [cls.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении устройств клиента {customer_id}: {e}")
            return []
    
    def validate(self) -> None:
        """
        Валидирует данные устройства.
        
        Raises:
            ValidationError: Если данные невалидны
        """
        errors = []
        
        # Валидация customer_id
        if not self.customer_id:
            errors.append("ID клиента обязателен")
        
        # Валидация device_type_id
        if not self.device_type_id:
            errors.append("ID типа устройства обязателен")
        
        # Валидация device_brand_id
        if not self.device_brand_id:
            errors.append("ID бренда устройства обязателен")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    @classmethod
    def create(cls, customer_id: int, device_type_id: int, 
               device_brand_id: int, serial_number: str = None) -> Optional['Device']:
        """
        Создает новое устройство.
        
        Args:
            customer_id: ID клиента
            device_type_id: ID типа устройства
            device_brand_id: ID бренда
            serial_number: Серийный номер (опционально)
            
        Returns:
            Device или None в случае ошибки
            
        Raises:
            ValidationError: Если данные невалидны
        """
        # Создаем временный экземпляр для валидации
        device = cls(customer_id=customer_id, device_type_id=device_type_id, 
                    device_brand_id=device_brand_id, serial_number=serial_number)
        device.validate()  # Валидация перед сохранением
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO devices (customer_id, device_type_id, device_brand_id, serial_number, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (device.customer_id, device.device_type_id, device.device_brand_id, device.serial_number))
                conn.commit()
                device_id = cursor.lastrowid
                return cls.get_by_id(device_id)
        except ValidationError:
            raise  # Пробрасываем ValidationError дальше
        except Exception as e:
            logger.error(f"Ошибка при создании устройства: {e}")
            raise ValidationError(f"Ошибка при создании устройства: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'device_type_id': self.device_type_id,
            'device_brand_id': self.device_brand_id,
            'serial_number': self.serial_number,
            'password': self.password,
            'symptom_tags': self.symptom_tags,
            'appearance_tags': self.appearance_tags,
            'comment': self.comment,
            'created_at': self.created_at,
            'device_type': self.device_type,
            'device_brand': self.device_brand,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email
        }

