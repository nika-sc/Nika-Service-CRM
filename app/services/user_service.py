"""
Сервис для работы с пользователями.
"""
from typing import Optional, Dict, List
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.database.connection import get_db_connection
from app.services.action_log_service import ActionLogService
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для работы с пользователями."""

    # Запрещенные права для кастомных ролей сотрудников.
    # Идея: если нужно "управление пользователями/настройками", это должна быть роль admin.
    RESTRICTED_CUSTOM_ROLE_PERMISSIONS = {"manage_users", "manage_settings"}

    @staticmethod
    def _get_permission_names_by_ids(permission_ids: List[int]) -> List[str]:
        """Возвращает список имен прав по списку ID."""
        if not permission_ids:
            return []
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT name FROM permissions WHERE id IN ({','.join(['?'] * len(permission_ids))})",
                    [int(pid) for pid in permission_ids],
                )
                return [row["name"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении имен прав по ID: {e}")
            return []

    @staticmethod
    def _validate_custom_role_permissions(permission_ids: List[int]):
        """Запрещает выдачу опасных прав в кастомных ролях."""
        names = set(UserService._get_permission_names_by_ids(permission_ids))
        forbidden = sorted(list(names.intersection(UserService.RESTRICTED_CUSTOM_ROLE_PERMISSIONS)))
        if forbidden:
            raise ValidationError(
                "Нельзя выдавать сотруднику права: " + ", ".join(forbidden) + ". "
                "Для этого используйте роль admin."
            )
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Хеширует пароль с использованием bcrypt (через werkzeug.security).
        Использует безопасное хеширование с солью для защиты от rainbow tables.
        
        Args:
            password: Пароль в открытом виде
            
        Returns:
            Хеш пароля в формате werkzeug (pbkdf2:sha256:...)
        """
        return generate_password_hash(password)
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Проверяет пароль против хеша.
        Поддерживает как старые SHA-256 хеши (для миграции), так и новые werkzeug хеши.
        
        Args:
            password: Пароль в открытом виде
            password_hash: Хеш пароля (может быть SHA-256 или werkzeug формат)
            
        Returns:
            True если пароль верный
        """
        if not password_hash:
            return False
        
        # Сначала пробуем проверить через werkzeug (работает для всех форматов werkzeug: pbkdf2, scrypt, argon2)
        try:
            result = check_password_hash(password_hash, password)
            if result:
                logger.debug(f"Пароль проверен успешно через werkzeug (формат: {password_hash[:20]}...)")
                return True
        except (ValueError, TypeError) as e:
            # Если хеш не в формате werkzeug, пробуем старый способ
            logger.debug(f"Хеш не в формате werkzeug, пробуем SHA-256: {e}")
        except Exception as e:
            # Логируем другие ошибки для диагностики
            logger.warning(f"Неожиданная ошибка при проверке пароля через werkzeug: {e}")
        
        # Для обратной совместимости: если старый SHA-256 хеш, проверяем его
        # SHA-256 хеш имеет длину 64 символа и состоит только из hex символов
        import hashlib
        if len(password_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in password_hash):
            old_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash.lower() == old_hash.lower():
                # Если пароль совпал со старым хешем, перехешируем его новым способом
                # Это делается при следующем входе пользователя
                logger.info(f"Обнаружен старый SHA-256 хеш, требуется перехеширование")
                return True
        
        return False
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict]:
        """
        Получает пользователя по имени пользователя.
        
        Args:
            username: Имя пользователя
            
        Returns:
            Словарь с данными пользователя или None
        """
        if not username or not username.strip():
            return None
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE username = ? AND is_active = 1",
                    (username.strip(),)
                )
                user = cursor.fetchone()
                if user:
                    user_dict = dict(user)
                    # Добавляем display_name с fallback на username для обратной совместимости
                    if not user_dict.get('display_name'):
                        user_dict['display_name'] = user_dict.get('username', '')
                    return user_dict
                return None
        except sqlite3.OperationalError as e:
            logger.error(f"Ошибка при получении пользователя {username}: {e}")
            return None
    
    @staticmethod
    def get_user_by_id(user_id: int, include_inactive: bool = False) -> Optional[Dict]:
        """
        Получает пользователя по ID.
        
        Args:
            user_id: ID пользователя
            include_inactive: Включать ли неактивных пользователей
            
        Returns:
            Словарь с данными пользователя или None
        """
        if not user_id or user_id <= 0:
            return None
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                if include_inactive:
                    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                else:
                    cursor.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,))
                user = cursor.fetchone()
                if user:
                    user_dict = dict(user)
                    # Добавляем display_name с fallback на username для обратной совместимости
                    if not user_dict.get('display_name'):
                        user_dict['display_name'] = user_dict.get('username', '')
                    return user_dict
                return None
        except sqlite3.OperationalError as e:
            logger.error(f"Ошибка при получении пользователя {user_id}: {e}")
            return None
    
    @staticmethod
    def create_user(username: str, password: str, role: str = 'viewer', display_name: str = None) -> Optional[int]:
        """
        Создает нового пользователя.
        
        Args:
            username: Имя пользователя (email для входа)
            password: Пароль
            role: Роль пользователя (viewer, master, manager, admin)
            display_name: Отображаемое имя (ФИО), если не указано - используется username
            
        Returns:
            ID созданного пользователя или None
        """
        if not username or not username.strip():
            raise ValidationError("Имя пользователя обязательно")
        
        if not password or len(password) < 4:
            raise ValidationError("Пароль должен быть не менее 4 символов")
        
        if role not in ['viewer', 'master', 'manager', 'admin']:
            raise ValidationError("Неверная роль пользователя")
        
        password_hash = UserService.hash_password(password)
        
        # Если display_name не указан, используем username
        if not display_name or not display_name.strip():
            display_name = username.strip()
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, password_hash, role, display_name, created_at, is_active)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
                ''', (username.strip(), password_hash, role, display_name.strip()))
                conn.commit()
                user_id_new = cursor.lastrowid
                
                # Логируем создание пользователя
                try:
                    from flask_login import current_user
                    from app.services.action_log_service import ActionLogService
                    
                    current_user_id = None
                    current_username = None
                    
                    # Пытаемся получить текущего пользователя
                    try:
                        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                            current_user_id = current_user.id
                            current_username = current_user.username
                    except Exception:
                        pass  # Если не удалось получить текущего пользователя, используем None
                    
                    # Логируем создание пользователя
                    ActionLogService.log_action(
                        user_id=current_user_id,
                        username=current_username,
                        action_type='create',
                        entity_type='user',
                        entity_id=user_id_new,
                        details={
                            'username': username.strip(),
                            'role': role
                        }
                    )
                    logger.info(f"Создание пользователя залогировано: {username.strip()} (ID: {user_id_new})")
                except Exception as e:
                    logger.error(f"Не удалось залогировать создание пользователя: {e}", exc_info=True)
                
                return user_id_new
        except sqlite3.IntegrityError:
            logger.error(f"Пользователь с именем {username} уже существует")
            raise ValidationError("Пользователь с таким именем уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
            raise DatabaseError(f"Ошибка при создании пользователя: {e}")
    
    @staticmethod
    def update_user_last_login(user_id: int) -> bool:
        """
        Обновляет время последнего входа пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        # Не логируем вход пользователя, это слишком частое событие
        if not user_id or user_id <= 0:
            return False
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении времени входа пользователя {user_id}: {e}")
            return False
    
    @staticmethod
    def check_role_permission(user_role: str, required_role: str) -> bool:
        """
        Проверяет, имеет ли пользователь с ролью user_role права для required_role.
        
        Иерархия ролей:
        - viewer: только просмотр (1)
        - master: мастер (2)
        - manager: менеджер (3)
        - admin: администратор (4) - все права
        
        Args:
            user_role: Роль пользователя
            required_role: Требуемая роль
            
        Returns:
            True если пользователь имеет права
        """
        role_hierarchy = {
            'viewer': 1,
            'master': 2,
            'manager': 3,
            'admin': 4
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 999)
        
        return user_level >= required_level
    
    @staticmethod
    def get_user_permissions(user_id: int) -> List[str]:
        """
        Получает список прав пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список имен прав
        """
        try:
            user = UserService.get_user_by_id(user_id)
            if not user:
                return []
            
            role = user.get('role', 'viewer')
            
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT p.name
                    FROM permissions AS p
                    INNER JOIN role_permissions AS rp ON rp.permission_id = p.id
                    WHERE rp.role = ?
                ''', (role,))
                
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении прав пользователя {user_id}: {e}")
            return []
    
    @staticmethod
    def rehash_password_if_needed(user_id: int, password: str, current_hash: str) -> bool:
        """
        Перехеширует пароль, если используется старый SHA-256 хеш.
        Вызывается после успешной проверки пароля со старым хешем.
        
        Args:
            user_id: ID пользователя
            password: Пароль в открытом виде (для перехеширования)
            current_hash: Текущий хеш пароля
            
        Returns:
            True если пароль был перехеширован
        """
        # Если хеш уже в формате werkzeug (pbkdf2, scrypt и т.д.), перехеширование не требуется
        if current_hash.startswith('pbkdf2:') or current_hash.startswith('scrypt:'):
            return False
        
        # Если это старый SHA-256 хеш, перехешируем
        try:
            new_hash = UserService.hash_password(password)
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET password_hash = ?
                    WHERE id = ?
                ''', (new_hash, user_id))
                conn.commit()
                logger.info(f"Пароль пользователя {user_id} успешно перехеширован")
                return True
        except Exception as e:
            logger.error(f"Ошибка при перехешировании пароля пользователя {user_id}: {e}")
            return False
    
    @staticmethod
    def check_permission(user_id: int, permission: str) -> bool:
        """
        Проверяет, имеет ли пользователь конкретное право.
        
        Args:
            user_id: ID пользователя
            permission: Имя права
            
        Returns:
            True если пользователь имеет право
        """
        try:
            user = UserService.get_user_by_id(user_id)
            if not user:
                return False
            
            role = (user.get('role') or 'viewer').strip()
            role_lower = role.lower()
            
            # Admin имеет все права
            if role_lower == 'admin':
                return True
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Проверяем права через role_permissions (сравнение роли без учёта регистра)
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM permissions AS p
                    INNER JOIN role_permissions AS rp ON rp.permission_id = p.id
                    WHERE LOWER(TRIM(rp.role)) = ? AND p.name = ?
                ''', (role_lower, permission))
                
                result = cursor.fetchone()[0] > 0
                logger.debug(f"Проверка права {permission} для пользователя {user_id} (роль: {role}): {result}")
                return result
        except Exception as e:
            logger.error(f"Ошибка при проверке права {permission} для пользователя {user_id}: {e}")
            return False
    
    @staticmethod
    def get_all_users(include_inactive: bool = False, role: Optional[str] = None) -> List[Dict]:
        """
        Получает список всех пользователей.
        
        Args:
            include_inactive: Включать ли неактивных пользователей
            role: Фильтр по роли (если None, то все роли)
            
        Returns:
            Список словарей с данными пользователей
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                query = 'SELECT * FROM users'
                conditions = []
                params = []
                
                if not include_inactive:
                    conditions.append('is_active = 1')
                
                if role:
                    conditions.append('role = ?')
                    params.append(role)
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
                
                query += ' ORDER BY created_at DESC'
                
                cursor.execute(query, params)
                users = [dict(row) for row in cursor.fetchall()]
                # Добавляем display_name с fallback на username для обратной совместимости
                for user in users:
                    if not user.get('display_name'):
                        user['display_name'] = user.get('username', '')
                return users
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}")
            return []
    
    @staticmethod
    def get_user_display_name(user_id: int) -> str:
        """
        Получает отображаемое имя пользователя (display_name или username).
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Отображаемое имя пользователя
        """
        user = UserService.get_user_by_id(user_id, include_inactive=True)
        if not user:
            return 'Неизвестный пользователь'
        
        return user.get('display_name') or user.get('username', 'Неизвестный пользователь')
    
    @staticmethod
    def update_user(user_id: int, username: str = None, role: str = None, is_active: int = None, display_name: str = None) -> bool:
        """
        Обновляет данные пользователя.
        
        Args:
            user_id: ID пользователя
            username: Новое имя пользователя (опционально)
            role: Новая роль (опционально)
            is_active: Новый статус активности (опционально)
            display_name: Отображаемое имя (ФИО) (опционально)
            
        Returns:
            True если успешно
        """
        if not user_id or user_id <= 0:
            raise ValidationError("Неверный ID пользователя")
        
        updates = []
        params = []
        
        if username is not None:
            if not username.strip():
                raise ValidationError("Имя пользователя не может быть пустым")
            updates.append("username = ?")
            params.append(username.strip())
        
        if role is not None:
            if role not in ['viewer', 'master', 'manager', 'admin']:
                raise ValidationError("Неверная роль пользователя")
            updates.append("role = ?")
            params.append(role)
        
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name.strip() if display_name.strip() else None)
        
        if not updates:
            return True  # Нет изменений
        
        params.append(user_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                
                # Логируем обновление
                try:
                    from flask_login import current_user
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
                        action_type='update',
                        entity_type='user',
                        entity_id=user_id,
                        details={'updates': dict(zip([u.split('=')[0].strip() for u in updates], params[:-1]))}
                    )
                except Exception as e:
                    logger.error(f"Не удалось залогировать обновление пользователя: {e}")
                
                return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            raise ValidationError("Пользователь с таким именем уже существует")
        except Exception as e:
            logger.error(f"Ошибка при обновлении пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении пользователя: {e}")
    
    @staticmethod
    def change_password(user_id: int, new_password: str) -> bool:
        """
        Изменяет пароль пользователя.
        
        Args:
            user_id: ID пользователя
            new_password: Новый пароль
            
        Returns:
            True если успешно
        """
        if not user_id or user_id <= 0:
            raise ValidationError("Неверный ID пользователя")
        
        if not new_password or len(new_password) < 4:
            raise ValidationError("Пароль должен быть не менее 4 символов")
        
        password_hash = UserService.hash_password(new_password)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET password_hash = ?
                    WHERE id = ?
                ''', (password_hash, user_id))
                conn.commit()
                
                # Логируем смену пароля
                try:
                    from flask_login import current_user
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
                        action_type='update',
                        entity_type='user',
                        entity_id=user_id,
                        details={'action': 'password_change'}
                    )
                except Exception as e:
                    logger.error(f"Не удалось залогировать смену пароля: {e}")
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при смене пароля пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при смене пароля: {e}")
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """
        Удаляет пользователя (помечает как неактивного).
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        if not user_id or user_id <= 0:
            raise ValidationError("Неверный ID пользователя")
        
        # Проверяем, что это не последний администратор
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                if user and user[0] == 'admin':
                    # Проверяем количество активных администраторов
                    cursor.execute('SELECT COUNT(*) FROM users WHERE role = ? AND is_active = 1', ('admin',))
                    admin_count = cursor.fetchone()[0]
                    if admin_count <= 1:
                        raise ValidationError("Нельзя удалить последнего администратора")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Ошибка при проверке возможности удаления пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при проверке возможности удаления: {e}")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users 
                    SET is_active = 0
                    WHERE id = ?
                ''', (user_id,))
                conn.commit()
                
                # Логируем удаление
                try:
                    from flask_login import current_user
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
                        action_type='delete',
                        entity_type='user',
                        entity_id=user_id
                    )
                except Exception as e:
                    logger.error(f"Не удалось залогировать удаление пользователя: {e}")
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении пользователя: {e}")
    
    @staticmethod
    def get_all_permissions() -> List[Dict]:
        """
        Получает список всех прав.
        
        Returns:
            Список словарей с данными прав
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM permissions ORDER BY name')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении списка прав: {e}")
            return []
    
    @staticmethod
    def update_permission(permission_id: int, description: str = None) -> bool:
        """
        Обновляет описание права.
        
        Args:
            permission_id: ID права
            description: Новое описание
            
        Returns:
            True если успешно
        """
        if not permission_id or permission_id <= 0:
            raise ValidationError("Неверный ID права")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE permissions 
                    SET description = ?
                    WHERE id = ?
                ''', (description, permission_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении права {permission_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении права: {e}")
    
    @staticmethod
    def get_all_roles() -> List[Dict]:
        """
        Получает список всех ролей с их правами.
        
        Returns:
            Список словарей с данными ролей и их прав
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                # Получаем все уникальные роли из role_permissions
                cursor.execute('''
                    SELECT DISTINCT role 
                    FROM role_permissions
                    ORDER BY role
                ''')
                roles = [row[0] for row in cursor.fetchall()]
                
                # Добавляем стандартные роли, если их нет
                standard_roles = ['viewer', 'master', 'manager', 'admin']
                for role in standard_roles:
                    if role not in roles:
                        roles.append(role)
                
                result = []
                for role in roles:
                    # Получаем права для роли
                    cursor.execute('''
                        SELECT p.id, p.name, p.description
                        FROM permissions AS p
                        INNER JOIN role_permissions AS rp ON rp.permission_id = p.id
                        WHERE rp.role = ?
                        ORDER BY p.name
                    ''', (role,))
                    permissions = [dict(row) for row in cursor.fetchall()]
                    
                    result.append({
                        'role': role,
                        'permissions': permissions
                    })
                
                return result
        except Exception as e:
            logger.error(f"Ошибка при получении списка ролей: {e}")
            return []
    
    @staticmethod
    def get_default_permission_ids_for_role(role: str) -> List[int]:
        """
        Получает список ID прав по умолчанию для стандартной роли.
        
        Args:
            role: Название роли ('master', 'manager', 'admin')
            
        Returns:
            Список ID прав
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT permission_id
                    FROM role_permissions
                    WHERE role = ?
                    ORDER BY permission_id
                ''', (role,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении прав по умолчанию для роли {role}: {e}")
            return []
    
    @staticmethod
    def create_role(role_name: str, permission_ids: List[int]) -> bool:
        """
        Создает новую роль с правами.
        
        Args:
            role_name: Название роли
            permission_ids: Список ID прав
            
        Returns:
            True если успешно
        """
        if not role_name or not role_name.strip():
            raise ValidationError("Название роли обязательно")
        
        role_name = role_name.strip().lower()
        
        # Проверяем, что роль не является стандартной
        standard_roles = ['viewer', 'master', 'manager', 'admin']
        if role_name in standard_roles:
            raise ValidationError("Нельзя создать стандартную роль")

        # Запрещаем опасные права в кастомных ролях
        UserService._validate_custom_role_permissions(permission_ids)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем старые права роли, если они есть
                cursor.execute('DELETE FROM role_permissions WHERE role = ?', (role_name,))
                
                # Добавляем новые права
                for perm_id in permission_ids:
                    cursor.execute('''
                        INSERT OR IGNORE INTO role_permissions (role, permission_id)
                        VALUES (?, ?)
                    ''', (role_name, perm_id))
                
                conn.commit()
                
                # Логируем создание роли
                try:
                    from flask_login import current_user
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
                        entity_type='role',
                        entity_id=None,
                        details={'role': role_name, 'permissions': permission_ids}
                    )
                except Exception as e:
                    logger.error(f"Не удалось залогировать создание роли: {e}")
                
                return True
        except Exception as e:
            logger.error(f"Ошибка при создании роли {role_name}: {e}")
            raise DatabaseError(f"Ошибка при создании роли: {e}")
    
    @staticmethod
    def update_role(role_name: str, permission_ids: List[int]) -> bool:
        """
        Обновляет права роли.
        
        Args:
            role_name: Название роли
            permission_ids: Список ID прав
            
        Returns:
            True если успешно
        """
        if not role_name or not role_name.strip():
            raise ValidationError("Название роли обязательно")
        
        role_name = role_name.strip().lower()

        # Запрещаем опасные права в кастомных ролях
        # (стандартные роли редактируются через миграции/код, а не через UI)
        standard_roles = ['viewer', 'master', 'manager', 'admin']
        if role_name not in standard_roles:
            UserService._validate_custom_role_permissions(permission_ids)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем старые права роли
                cursor.execute('DELETE FROM role_permissions WHERE role = ?', (role_name,))
                
                # Добавляем новые права
                for perm_id in permission_ids:
                    cursor.execute('''
                        INSERT OR IGNORE INTO role_permissions (role, permission_id)
                        VALUES (?, ?)
                    ''', (role_name, perm_id))
                
                conn.commit()
                
                # Логируем обновление роли
                try:
                    from flask_login import current_user
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
                        action_type='update',
                        entity_type='role',
                        entity_id=None,
                        details={'role': role_name, 'permissions': permission_ids}
                    )
                except Exception as e:
                    logger.error(f"Не удалось залогировать обновление роли: {e}")
                
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении роли {role_name}: {e}")
            raise DatabaseError(f"Ошибка при обновлении роли: {e}")
    
    @staticmethod
    def delete_role(role_name: str) -> bool:
        """
        Удаляет роль.
        
        Args:
            role_name: Название роли
            
        Returns:
            True если успешно
        """
        if not role_name or not role_name.strip():
            raise ValidationError("Название роли обязательно")
        
        role_name = role_name.strip().lower()
        
        # Проверяем, что роль не является стандартной
        standard_roles = ['viewer', 'master', 'manager', 'admin']
        if role_name in standard_roles:
            raise ValidationError("Нельзя удалить стандартную роль")
        
        # Проверяем, что роль не используется
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users WHERE role = ? AND is_active = 1', (role_name,))
                user_count = cursor.fetchone()[0]
                if user_count > 0:
                    raise ValidationError(f"Роль используется {user_count} пользователем(ами). Сначала измените роли пользователей.")
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Ошибка при проверке использования роли {role_name}: {e}")
            raise DatabaseError(f"Ошибка при проверке использования роли: {e}")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM role_permissions WHERE role = ?', (role_name,))
                conn.commit()
                
                # Логируем удаление роли
                try:
                    from flask_login import current_user
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
                        action_type='delete',
                        entity_type='role',
                        entity_id=None,
                        details={'role': role_name}
                    )
                except Exception as e:
                    logger.error(f"Не удалось залогировать удаление роли: {e}")
                
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении роли {role_name}: {e}")
            raise DatabaseError(f"Ошибка при удалении роли: {e}")

