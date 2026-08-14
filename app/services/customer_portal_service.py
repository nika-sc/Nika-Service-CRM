"""
Сервис для личного кабинета клиента.
"""
from typing import Optional, Dict
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
import sqlite3
import logging
import secrets
import string
from datetime import timedelta
from app.utils.datetime_utils import get_moscow_now_naive

logger = logging.getLogger(__name__)


class CustomerPortalService:
    """Сервис для личного кабинета клиента."""
    
    @staticmethod
    def generate_simple_password(length: int = 8) -> str:
        """
        Генерирует простой пароль из букв и цифр.
        
        Args:
            length: Длина пароля (по умолчанию 8)
            
        Returns:
            Сгенерированный пароль
        """
        # Используем только буквы (латиница) и цифры
        characters = string.ascii_letters + string.digits
        # Исключаем похожие символы для удобства чтения
        characters = characters.replace('0', '').replace('O', '').replace('o', '')
        characters = characters.replace('1', '').replace('I', '').replace('l', '')
        
        password = ''.join(secrets.choice(characters) for _ in range(length))
        return password
    
    @staticmethod
    def generate_token(customer_id: int, expires_days: int = 90) -> str:
        """Генерирует токен доступа для клиента (ссылка задать пароль / вход)."""
        token = secrets.token_urlsafe(32)
        expires_at = get_moscow_now_naive() + timedelta(days=expires_days)
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO customer_tokens 
                    (customer_id, token, expires_at, created_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (customer_id, token, expires_at.isoformat(sep=' ', timespec='seconds')))
                conn.commit()
                return token
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при создании токена: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")

    @staticmethod
    def _token_not_expired(expires_at) -> bool:
        if expires_at is None:
            return True
        from datetime import datetime
        if isinstance(expires_at, datetime):
            exp = expires_at.replace(tzinfo=None) if expires_at.tzinfo else expires_at
        else:
            raw = str(expires_at).replace('T', ' ').replace('Z', '')
            try:
                exp = datetime.fromisoformat(raw[:19])
            except ValueError:
                return False
        return exp > get_moscow_now_naive()
    
    @staticmethod
    def validate_token(token: str) -> Optional[Dict]:
        """Проверяет токен и возвращает данные клиента."""
        if not token or len(token) > 200:
            return None
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        ct.customer_id,
                        ct.expires_at,
                        c.name,
                        c.phone,
                        c.email,
                        c.portal_enabled
                    FROM customer_tokens ct
                    JOIN customers c ON c.id = ct.customer_id
                    WHERE ct.token = ?
                    AND c.portal_enabled = 1
                ''', (token,))
                row = cursor.fetchone()
                if not row:
                    return None
                if not CustomerPortalService._token_not_expired(row['expires_at']):
                    return None
                cursor.execute('''
                    UPDATE customer_tokens
                    SET last_used_at = CURRENT_TIMESTAMP
                    WHERE token = ?
                ''', (token,))
                conn.commit()
                return {
                    'customer_id': row['customer_id'],
                    'name': row['name'],
                    'phone': row['phone'],
                    'email': row['email']
                }
        except Exception as e:
            logger.error(f"Ошибка при проверке токена: {e}")
            return None
    
    @staticmethod
    def authenticate_by_password(phone: str, password: str) -> Optional[Dict]:
        """Аутентификация клиента по телефону и паролю."""
        try:
            from app.models.customer import Customer
            from app.utils.validators import normalize_phone
            from werkzeug.security import check_password_hash
            
            # Нормализуем телефон перед поиском
            normalized_phone = normalize_phone(phone)
            customer = Customer.get_by_phone(normalized_phone)
            if not customer:
                return None
            
            if not customer.portal_enabled:
                return None
            
            if not customer.portal_password_hash:
                return None

            from app.utils.validators import password_eligible_for_verify
            if not password_eligible_for_verify(password):
                return None
            
            if not check_password_hash(customer.portal_password_hash, password):
                return None
            
            # Проверяем, нужно ли сменить пароль (первый вход)
            needs_password_change = CustomerPortalService.check_needs_password_change(customer.id)
            
            return {
                'customer_id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
                'needs_password_change': needs_password_change
            }
        except Exception as e:
            logger.error(f"Ошибка при аутентификации клиента: {e}")
            return None
    
    @staticmethod
    def check_needs_password_change(customer_id: int) -> bool:
        """Проверяет, нужно ли сменить пароль (первый вход)."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT portal_password_changed FROM customers WHERE id = ?
                ''', (customer_id,))
                row = cursor.fetchone()
                if row:
                    # Если portal_password_changed = 0 или NULL, значит пароль не менялся
                    return not (row['portal_password_changed'] or 0)
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке необходимости смены пароля: {e}")
            return False
    
    @staticmethod
    def mark_password_changed(customer_id: int) -> bool:
        """Отмечает, что пароль был изменен клиентом."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE customers
                    SET portal_password_changed = 1
                    WHERE id = ?
                ''', (customer_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при отметке смены пароля: {e}")
            return False
    
    @staticmethod
    def set_portal_password(customer_id: int, password: str, reset_change_flag: bool = True) -> bool:
        """
        Устанавливает пароль для портала.
        
        Args:
            customer_id: ID клиента
            password: Пароль (минимум 6 символов)
            reset_change_flag: Если True, сбрасывает флаг смены пароля (для админа)
        """
        try:
            from app.utils.validators import password_meets_policy
            if not password_meets_policy(password):
                return False
            from werkzeug.security import generate_password_hash
            
            password_hash = generate_password_hash(password)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if reset_change_flag:
                    # Админ устанавливает пароль - сбрасываем флаг смены
                    cursor.execute('''
                        UPDATE customers
                        SET portal_password_hash = ?, portal_enabled = 1, portal_password_changed = 0
                        WHERE id = ?
                    ''', (password_hash, customer_id))
                else:
                    # Клиент меняет пароль - устанавливаем флаг
                    cursor.execute('''
                        UPDATE customers
                        SET portal_password_hash = ?, portal_enabled = 1, portal_password_changed = 1
                        WHERE id = ?
                    ''', (password_hash, customer_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при установке пароля портала: {e}")
            return False
    
    @staticmethod
    def generate_and_set_portal_password(customer_id: int) -> Optional[str]:
        """
        Генерирует и устанавливает случайный пароль для портала.
        
        Returns:
            Сгенерированный пароль или None в случае ошибки
        """
        try:
            password = CustomerPortalService.generate_simple_password()
            if CustomerPortalService.set_portal_password(customer_id, password, reset_change_flag=True):
                return password
            return None
        except Exception as e:
            logger.error(f"Ошибка при генерации пароля портала: {e}")
            return None

    @staticmethod
    def log_portal_password_generated(customer_id: int, customer_name: str = '', customer_phone: str = '') -> None:
        """Аудит выдачи пароля ЛК без plaintext."""
        logger.info("Сгенерирован пароль портала для клиента %s (plaintext не сохраняется)", customer_id)
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
                description=f"Сгенерирован пароль портала для клиента {customer_name or customer_id}",
                details={
                    'customer_id': customer_id,
                    'customer_name': customer_name,
                    'customer_phone': customer_phone,
                    'note': 'Plaintext пароля не хранится. Staff видит его один раз при создании/сбросе.',
                }
            )
        except Exception as e:
            logger.warning("Не удалось записать аудит пароля портала: %s", e)
    
    @staticmethod
    def enable_portal(customer_id: int) -> bool:
        """Включает доступ к порталу для клиента."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE customers
                    SET portal_enabled = 1
                    WHERE id = ?
                ''', (customer_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при включении портала: {e}")
            return False
    
    @staticmethod
    def disable_portal(customer_id: int) -> bool:
        """Отключает доступ к порталу для клиента."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Удаляем все токены клиента
                cursor.execute('DELETE FROM customer_tokens WHERE customer_id = ?', (customer_id,))
                cursor.execute('''
                    UPDATE customers
                    SET portal_enabled = 0, portal_password_hash = NULL
                    WHERE id = ?
                ''', (customer_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при отключении портала: {e}")
            return False
    
    @staticmethod
    def revoke_token(token: str) -> bool:
        """Отзывает токен."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM customer_tokens WHERE token = ?', (token,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при отзыве токена: {e}")
            return False
