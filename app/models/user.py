"""
Модель пользователя.
"""
from typing import Optional, Dict, Any
from app.models.base import BaseModel
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError
import sqlite3
import logging

logger = logging.getLogger(__name__)


class User(BaseModel):
    """
    Модель пользователя.
    
    Атрибуты:
        id: ID пользователя
        username: Имя пользователя (уникальное)
        password_hash: Хеш пароля
        role: Роль (viewer, master, manager, admin)
        created_at: Дата создания
        last_login: Дата последнего входа
        is_active: Активен ли пользователь
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.username = kwargs.get('username', '')
        self.password_hash = kwargs.get('password_hash', '')
        self.role = kwargs.get('role', 'viewer')
        self.created_at = kwargs.get('created_at')
        self.last_login = kwargs.get('last_login')
        self.is_active = kwargs.get('is_active', 1)
    
    def validate(self) -> None:
        """
        Валидирует данные пользователя.
        
        Raises:
            ValidationError: Если данные невалидны
        """
        errors = []
        
        # Валидация имени пользователя
        if not self.username or not self.username.strip():
            errors.append("Имя пользователя обязательно")
        elif len(self.username.strip()) < 3:
            errors.append("Имя пользователя должно быть не менее 3 символов")
        
        # Валидация роли
        if self.role not in ['viewer', 'master', 'manager', 'admin']:
            errors.append("Неверная роль пользователя")
        
        # Валидация пароля (только если это новый пользователь)
        if not self.id and not self.password_hash:
            errors.append("Пароль обязателен")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    @classmethod
    def get_by_id(cls, user_id: int) -> Optional['User']:
        """
        Получает пользователя по ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            User или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM users WHERE id = ? AND is_active = 1
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
            return None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """
        Получает пользователя по имени пользователя.
        
        Args:
            username: Имя пользователя
            
        Returns:
            User или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM users WHERE username = ? AND is_active = 1
                ''', (username,))
                
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя по имени {username}: {e}")
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь (без пароля)."""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_active': self.is_active
        }

