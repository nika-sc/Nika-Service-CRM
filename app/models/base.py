"""
Базовая модель для всех моделей данных.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.utils.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class BaseModel:
    """
    Базовый класс для всех моделей данных.
    Предоставляет общие методы для работы с данными.
    """
    
    def __init__(self, **kwargs):
        """Инициализация модели из словаря данных."""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Создает экземпляр модели из словаря.
        
        Args:
            data: Словарь с данными
            
        Returns:
            Экземпляр модели
        """
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует модель в словарь.
        
        Returns:
            Словарь с данными модели
        """
        result = {}
        for key, value in self.__dict__.items():
            # Пропускаем приватные атрибуты
            if not key.startswith('_'):
                # Преобразуем datetime в строку
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result
    
    def __repr__(self) -> str:
        """Строковое представление модели."""
        class_name = self.__class__.__name__
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.to_dict().items() if not k.startswith('_'))
        return f"{class_name}({attrs})"
    
    def __eq__(self, other) -> bool:
        """Сравнение моделей по ID."""
        if not isinstance(other, self.__class__):
            return False
        return getattr(self, 'id', None) == getattr(other, 'id', None)
    
    def __hash__(self) -> int:
        """Хеш модели для использования в множествах."""
        return hash((self.__class__, getattr(self, 'id', None)))
    
    def validate(self) -> None:
        """
        Валидирует данные модели.
        Должен быть переопределен в дочерних классах.
        
        Raises:
            ValidationError: Если данные невалидны
        """
        pass  # Базовая реализация - без валидации

