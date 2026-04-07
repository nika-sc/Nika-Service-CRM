"""
Настройка аутентификации и авторизации.
"""
import logging
from flask_login import LoginManager, UserMixin
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class User(UserMixin):
    """
    Класс пользователя для Flask-Login.
    """
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.username = user_dict['username']
        self.role = user_dict.get('role', 'viewer')
        self._is_active = user_dict.get('is_active', 1) == 1
    
    @property
    def is_active(self):
        return self._is_active


def setup_auth(login_manager: LoginManager):
    """
    Настраивает аутентификацию для Flask-Login.
    
    Args:
        login_manager: Экземпляр LoginManager
    """
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """
        Загружает пользователя по ID для Flask-Login.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            User: Объект пользователя или None
        """
        try:
            user_dict = UserService.get_user_by_id(int(user_id))
            if user_dict:
                return User(user_dict)
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при загрузке пользователя {user_id}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при загрузке пользователя {user_id}: {e}")
        return None

