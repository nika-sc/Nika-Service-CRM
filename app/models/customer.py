"""
Модель клиента.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.base import BaseModel
from app.database.connection import get_db_connection
from app.utils.validators import validate_phone, validate_email
from app.utils.exceptions import ValidationError
import sqlite3
import logging

logger = logging.getLogger(__name__)


class Customer(BaseModel):
    """
    Модель клиента.
    
    Атрибуты:
        id: ID клиента
        name: ФИО/название компании
        phone: Телефон (уникальный)
        email: Email
        created_at: Дата создания
        updated_at: Дата обновления
        devices_count: Количество устройств (вычисляемое)
        orders_count: Количество заявок (вычисляемое)
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.name = kwargs.get('name', '')
        self.phone = kwargs.get('phone', '')
        self.email = kwargs.get('email')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        self.devices_count = kwargs.get('devices_count', 0)
        self.orders_count = kwargs.get('orders_count', 0)
        self.portal_enabled = kwargs.get('portal_enabled', 0) or 0
        self.portal_password_hash = kwargs.get('portal_password_hash')
        self.portal_password_changed = kwargs.get('portal_password_changed', 0) or 0
    
    def validate(self) -> None:
        """
        Валидирует данные клиента.
        
        Raises:
            ValidationError: Если данные невалидны
        """
        errors = []
        
        # Валидация имени
        if not self.name or not self.name.strip():
            errors.append("Имя клиента не может быть пустым")
        
        # Валидация телефона
        if not self.phone or not self.phone.strip():
            errors.append("Номер телефона обязателен")
        else:
            try:
                self.phone = validate_phone(self.phone)
            except ValidationError as e:
                errors.append(str(e))
        
        # Валидация email (если указан)
        if self.email and self.email.strip():
            try:
                self.email = validate_email(self.email)
            except ValidationError as e:
                errors.append(str(e))
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    @classmethod
    def get_by_id(cls, customer_id: int) -> Optional['Customer']:
        """
        Получает клиента по ID.
        
        Args:
            customer_id: ID клиента
            
        Returns:
            Customer или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        c.*,
                        COALESCE(c.portal_enabled, 0) as portal_enabled,
                        COALESCE(c.portal_password_changed, 0) as portal_password_changed,
                        COUNT(DISTINCT d.id) as devices_count,
                        COUNT(DISTINCT o.id) as orders_count
                    FROM customers c
                    LEFT JOIN devices d ON d.customer_id = c.id
                    LEFT JOIN orders o ON o.customer_id = c.id AND (o.hidden = 0 OR o.hidden IS NULL)
                    WHERE c.id = ?
                    GROUP BY c.id
                ''', (customer_id,))
                
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении клиента {customer_id}: {e}")
            return None
    
    @classmethod
    def get_by_phone(cls, phone: str) -> Optional['Customer']:
        """
        Получает клиента по телефону.
        
        Args:
            phone: Номер телефона
            
        Returns:
            Customer или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        c.*,
                        COALESCE(c.portal_enabled, 0) as portal_enabled,
                        COALESCE(c.portal_password_changed, 0) as portal_password_changed
                    FROM customers c
                    WHERE c.phone = ?
                ''', (phone,))
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении клиента по телефону {phone}: {e}")
            return None
    
    @classmethod
    def create(cls, name: str, phone: str, email: str = None) -> Optional['Customer']:
        """
        Создает нового клиента.
        
        Args:
            name: Имя клиента
            phone: Телефон
            email: Email (опционально)
            
        Returns:
            Customer или None в случае ошибки
            
        Raises:
            ValidationError: Если данные невалидны
        """
        # Создаем временный экземпляр для валидации
        customer = cls(name=name, phone=phone, email=email)
        customer.validate()  # Валидация перед сохранением
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO customers (name, phone, email, created_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (customer.name, customer.phone, customer.email))
                conn.commit()
                customer_id = cursor.lastrowid
                
                # Автоматически генерируем пароль для портала
                try:
                    from app.services.customer_portal_service import CustomerPortalService
                    generated_password = CustomerPortalService.generate_and_set_portal_password(customer_id)
                    if generated_password:
                        logger.info(f"Автоматически сгенерирован пароль портала для клиента {customer_id}: {generated_password}")
                        
                        # Сохраняем пароль в action_logs для возможности просмотра администратором
                        try:
                            from flask_login import current_user
                            from app.services.action_log_service import ActionLogService
                            
                            current_user_id = None
                            current_username = None
                            try:
                                if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                                    current_user_id = current_user.id
                                    current_username = current_user.username
                            except Exception:
                                pass
                            
                            ActionLogService.log_action(
                                user_id=current_user_id,
                                username=current_username,
                                action_type='create',
                                entity_type='customer_portal_password',
                                entity_id=customer_id,
                                description=f"Автоматически сгенерирован пароль портала для клиента {customer.name}",
                                details={
                                    'customer_id': customer_id,
                                    'customer_name': customer.name,
                                    'customer_phone': customer.phone,
                                    'generated_password': generated_password,
                                    'note': 'Пароль сохранен в захешированном виде. При первом входе клиент должен сменить пароль.'
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Не удалось сохранить пароль в action_logs: {e}")
                except Exception as e:
                    logger.warning(f"Не удалось автоматически установить пароль портала для клиента {customer_id}: {e}")
                
                return cls.get_by_id(customer_id)
        except sqlite3.IntegrityError as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            logger.error(f"Ошибка при создании клиента: {e}")
            raise ValidationError(error_msg)
        except ValidationError:
            raise  # Пробрасываем ValidationError дальше
        except Exception as e:
            logger.error(f"Ошибка при создании клиента: {e}")
            raise ValidationError(f"Ошибка при создании клиента: {e}")
    
    def update(self, name: str = None, phone: str = None, email: str = None) -> bool:
        """
        Обновляет данные клиента.
        
        Args:
            name: Новое имя
            phone: Новый телефон
            email: Новый email
            
        Returns:
            True если успешно, False в случае ошибки
            
        Raises:
            ValidationError: Если данные невалидны
        """
        if not self.id:
            raise ValidationError("Нельзя обновить клиента без ID")
        
        # Обновляем атрибуты для валидации
        if name is not None:
            self.name = name
        if phone is not None:
            self.phone = phone
        if email is not None:
            self.email = email
        
        # Валидация обновленных данных
        self.validate()
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(self.name)
                
                if phone is not None:
                    updates.append("phone = ?")
                    params.append(self.phone)
                
                if email is not None:
                    updates.append("email = ?")
                    params.append(self.email)
                
                if updates:
                    updates.append("updated_at = CURRENT_TIMESTAMP")
                    params.append(self.id)
                    cursor.execute(
                        f"UPDATE customers SET {', '.join(updates)} WHERE id = ?",
                        params
                    )
                    conn.commit()
                    return True
                return False
        except ValidationError:
            raise  # Пробрасываем ValidationError дальше
        except sqlite3.IntegrityError as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            logger.error(f"Ошибка при обновлении клиента: {e}")
            raise ValidationError(error_msg)
        except Exception as e:
            logger.error(f"Ошибка при обновлении клиента {self.id}: {e}")
            raise ValidationError(f"Ошибка при обновлении клиента: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'devices_count': self.devices_count,
            'orders_count': self.orders_count,
            'portal_enabled': self.portal_enabled,
            'portal_password_hash': bool(self.portal_password_hash),  # Только флаг наличия, не сам хеш
            'portal_password_changed': self.portal_password_changed
        }

