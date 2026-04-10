"""
Сервис для работы с мастерами.
"""
from typing import Dict, List, Optional, Any
from app.database.queries.reference_queries import ReferenceQueries
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.error_handlers import handle_service_error
import sqlite3
import logging

logger = logging.getLogger(__name__)


class MasterService:
    """Сервис для работы с мастерами."""
    
    @staticmethod
    @handle_service_error
    def get_all_masters(active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Получает всех мастеров.
        
        Args:
            active_only: Только активные мастера
            
        Returns:
            Список мастеров
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                query = '''
                    SELECT 
                        id, name, salary_rule_type, salary_rule_value,
                        salary_percent_services, salary_percent_parts, salary_percent_shop_parts,
                        active, comment, created_at, updated_at, user_id
                    FROM masters
                '''
                if active_only:
                    query += ' WHERE active = 1 OR active IS NULL'
                query += ' ORDER BY name'
                
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении мастеров: {e}", exc_info=True)
            return []
    
    @staticmethod
    @handle_service_error
    def get_master_by_id(master_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает мастера по ID.
        
        Args:
            master_id: ID мастера
            
        Returns:
            Словарь с данными мастера или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        id, name, salary_rule_type, salary_rule_value,
                        salary_percent_services, salary_percent_parts, salary_percent_shop_parts,
                        active, comment, created_at, updated_at, user_id
                    FROM masters
                    WHERE id = ?
                ''', (master_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении мастера {master_id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    @handle_service_error
    def create_master(
        name: str,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None,
        salary_percent_services: Optional[float] = None,
        salary_percent_parts: Optional[float] = None,
        salary_percent_shop_parts: Optional[float] = None,
        active: int = 1,
        comment: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> int:
        """
        Создает нового мастера.
        
        Args:
            name: Имя мастера
            salary_rule_type: Тип правила зарплаты ('percent' или 'fixed')
            salary_rule_value: Значение правила (процент 0-100 или сумма в копейках)
            active: Активен ли мастер (1 = да)
            comment: Комментарий
            
        Returns:
            ID созданного мастера
        """
        if not name or not name.strip():
            raise ValidationError("Имя мастера не может быть пустым")
        
        if salary_rule_type and salary_rule_type not in ['percent', 'fixed']:
            raise ValidationError("Тип правила зарплаты должен быть 'percent' или 'fixed'")
        
        if salary_rule_type and salary_rule_value is None:
            raise ValidationError("Необходимо указать значение правила зарплаты")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO masters (name, salary_rule_type, salary_rule_value,
                        salary_percent_services, salary_percent_parts, salary_percent_shop_parts,
                        active, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name.strip(), salary_rule_type, salary_rule_value,
                      salary_percent_services, salary_percent_parts, salary_percent_shop_parts,
                      active, comment))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValidationError(f"Мастер с именем '{name}' уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании мастера: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при создании мастера: {e}")
    
    @staticmethod
    @handle_service_error
    def update_master(
        master_id: int,
        name: Optional[str] = None,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None,
        salary_percent_services: Optional[float] = None,
        salary_percent_parts: Optional[float] = None,
        salary_percent_shop_parts: Optional[float] = None,
        active: Optional[int] = None,
        comment: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Обновляет мастера.
        
        Args:
            master_id: ID мастера
            ... (остальные параметры как в create_master)
            
        Returns:
            True если успешно
        """
        master = MasterService.get_master_by_id(master_id)
        if not master:
            raise NotFoundError(f"Мастер с ID {master_id} не найден")
        
        if name is not None and not name.strip():
            raise ValidationError("Имя мастера не может быть пустым")
        
        if salary_rule_type and salary_rule_type not in ['percent', 'fixed']:
            raise ValidationError("Тип правила зарплаты должен быть 'percent' или 'fixed'")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if name is not None:
                    updates.append('name = ?')
                    params.append(name.strip())
                if salary_rule_type is not None:
                    updates.append('salary_rule_type = ?')
                    params.append(salary_rule_type)
                if salary_rule_value is not None:
                    updates.append('salary_rule_value = ?')
                    params.append(salary_rule_value)
                if salary_percent_services is not None:
                    updates.append('salary_percent_services = ?')
                    params.append(salary_percent_services)
                if salary_percent_parts is not None:
                    updates.append('salary_percent_parts = ?')
                    params.append(salary_percent_parts)
                if salary_percent_shop_parts is not None:
                    updates.append('salary_percent_shop_parts = ?')
                    params.append(salary_percent_shop_parts)
                if active is not None:
                    updates.append('active = ?')
                    params.append(active)
                if comment is not None:
                    updates.append('comment = ?')
                    params.append(comment)
                if user_id is not None:
                    updates.append('user_id = ?')
                    params.append(user_id)
                
                if not updates:
                    return False
                
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(master_id)
                
                cursor.execute(
                    f'UPDATE masters SET {", ".join(updates)} WHERE id = ?',
                    params
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            raise ValidationError(f"Мастер с именем '{name}' уже существует")
        except Exception as e:
            logger.error(f"Ошибка при обновлении мастера {master_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при обновлении мастера: {e}")
    
    @staticmethod
    @handle_service_error
    def delete_master(master_id: int) -> bool:
        """
        Удаляет мастера и связанного пользователя (только если он не используется в заявках).
        
        Args:
            master_id: ID мастера
            
        Returns:
            True если успешно
        """
        master = MasterService.get_master_by_id(master_id)
        if not master:
            raise NotFoundError(f"Мастер с ID {master_id} не найден")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем использование
                cursor.execute('SELECT COUNT(*) FROM orders WHERE master_id = ?', (master_id,))
                count = cursor.fetchone()[0]
                if count > 0:
                    raise ValidationError(f"Мастер используется в {count} заявках. Удаление невозможно.")
                
                # Получаем user_id перед удалением
                user_id = master.get('user_id')
                custom_role_name = f'master_{master_id}'
                
                # Удаляем связанного пользователя и роль, если есть
                if user_id:
                    try:
                        from app.services.user_service import UserService
                        
                        # Сначала удаляем пользователя (физически)
                        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                        if cursor.rowcount > 0:
                            logger.info(f"Удален пользователь ID={user_id}, связанный с мастером {master_id}")
                        
                        # Затем удаляем кастомную роль (после удаления пользователя проверка использования не сработает)
                        # Удаляем напрямую из role_permissions, так как пользователь уже удален
                        try:
                            cursor.execute('DELETE FROM role_permissions WHERE role = ?', (custom_role_name,))
                            if cursor.rowcount > 0:
                                logger.info(f"Удалена кастомная роль {custom_role_name}")
                        except Exception as e:
                            logger.warning(f"Не удалось удалить роль {custom_role_name}: {e}")
                    except Exception as e:
                        logger.warning(f"Не удалось удалить пользователя {user_id}: {e}")
                        # Продолжаем выполнение, даже если не удалось удалить пользователя
                
                # Удаляем мастера
                cursor.execute('DELETE FROM masters WHERE id = ?', (master_id,))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении мастера {master_id}: {e}", exc_info=True)
            raise


