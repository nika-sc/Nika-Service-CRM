"""
Сервис для работы с менеджерами.
"""
from typing import Dict, List, Optional, Any
from app.database.queries.reference_queries import ReferenceQueries
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.error_handlers import handle_service_error
import sqlite3
import logging

logger = logging.getLogger(__name__)


class ManagerService:
    """Сервис для работы с менеджерами."""
    
    @staticmethod
    @handle_service_error
    def get_all_managers(active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Получает всех менеджеров.
        
        Args:
            active_only: Только активные менеджеры
            
        Returns:
            Список менеджеров
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(managers)")
                cols = [row[1] for row in cursor.fetchall()]
                has_salary_rule_base = "salary_rule_base" in cols
                sel = (
                    "id, name, salary_rule_type, salary_rule_value, "
                    "salary_percent_services, salary_percent_parts, salary_percent_shop_parts, "
                    + ("COALESCE(salary_rule_base, 'profit') as salary_rule_base, " if has_salary_rule_base else "")
                    + "active, comment, created_at, updated_at, user_id"
                )
                query = f"SELECT {sel} FROM managers"
                if active_only:
                    query += " WHERE active = 1 OR active IS NULL"
                query += " ORDER BY name"
                cursor.execute(query)
                rows = [dict(row) for row in cursor.fetchall()]
                if not has_salary_rule_base:
                    for r in rows:
                        r["salary_rule_base"] = "profit"
                return rows
        except Exception as e:
            logger.error(f"Ошибка при получении менеджеров: {e}", exc_info=True)
            return []
    
    @staticmethod
    @handle_service_error
    def get_manager_by_id(manager_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает менеджера по ID.
        
        Args:
            manager_id: ID менеджера
            
        Returns:
            Словарь с данными менеджера или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(managers)")
                cols = [row[1] for row in cursor.fetchall()]
                has_salary_rule_base = "salary_rule_base" in cols
                sel = (
                    "id, name, salary_rule_type, salary_rule_value, "
                    "salary_percent_services, salary_percent_parts, salary_percent_shop_parts, "
                    + ("COALESCE(salary_rule_base, 'profit') as salary_rule_base, " if has_salary_rule_base else "")
                    + "active, comment, created_at, updated_at, user_id"
                )
                cursor.execute(f"SELECT {sel} FROM managers WHERE id = ?", (manager_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                d = dict(row)
                if not has_salary_rule_base:
                    d["salary_rule_base"] = "profit"
                return d
        except Exception as e:
            logger.error(f"Ошибка при получении менеджера {manager_id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    @handle_service_error
    def create_manager(
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
        Создает нового менеджера.
        
        Args:
            name: Имя менеджера
            salary_rule_type: Тип правила зарплаты ('percent' или 'fixed')
            salary_rule_value: Значение правила (процент 0-100 или сумма в копейках)
            active: Активен ли менеджер (1 = да)
            comment: Комментарий
            
        Returns:
            ID созданного менеджера
        """
        if not name or not name.strip():
            raise ValidationError("Имя менеджера не может быть пустым")
        
        if salary_rule_type and salary_rule_type not in ['percent', 'fixed']:
            raise ValidationError("Тип правила зарплаты должен быть 'percent' или 'fixed'")
        
        if salary_rule_type and salary_rule_value is None:
            raise ValidationError("Необходимо указать значение правила зарплаты")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO managers (name, salary_rule_type, salary_rule_value,
                        salary_percent_services, salary_percent_parts, salary_percent_shop_parts,
                        active, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name.strip(), salary_rule_type, salary_rule_value,
                      salary_percent_services, salary_percent_parts, salary_percent_shop_parts,
                      active, comment))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValidationError(f"Менеджер с именем '{name}' уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании менеджера: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при создании менеджера: {e}")
    
    @staticmethod
    @handle_service_error
    def update_manager(
        manager_id: int,
        name: Optional[str] = None,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None,
        salary_rule_base: Optional[str] = None,
        salary_percent_services: Optional[float] = None,
        salary_percent_parts: Optional[float] = None,
        salary_percent_shop_parts: Optional[float] = None,
        active: Optional[int] = None,
        comment: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Обновляет менеджера.
        
        Args:
            manager_id: ID менеджера
            ... (остальные параметры как в create_manager)
            
        Returns:
            True если успешно
        """
        manager = ManagerService.get_manager_by_id(manager_id)
        if not manager:
            raise NotFoundError(f"Менеджер с ID {manager_id} не найден")
        
        if name is not None and not name.strip():
            raise ValidationError("Имя менеджера не может быть пустым")
        
        if salary_rule_type and salary_rule_type not in ['percent', 'fixed']:
            raise ValidationError("Тип правила зарплаты должен быть 'percent' или 'fixed'")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(managers)")
                cols = [row[1] for row in cursor.fetchall()]
                has_salary_rule_base = "salary_rule_base" in cols
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
                if has_salary_rule_base and salary_rule_base is not None and salary_rule_base.strip().lower() in ('profit', 'revenue'):
                    updates.append('salary_rule_base = ?')
                    params.append(salary_rule_base.strip().lower())
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
                params.append(manager_id)
                
                cursor.execute(
                    f'UPDATE managers SET {", ".join(updates)} WHERE id = ?',
                    params
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            raise ValidationError(f"Менеджер с именем '{name}' уже существует")
        except Exception as e:
            logger.error(f"Ошибка при обновлении менеджера {manager_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при обновлении менеджера: {e}")
    
    @staticmethod
    @handle_service_error
    def delete_manager(manager_id: int) -> bool:
        """
        Удаляет менеджера и связанного пользователя (только если он не используется в заявках).
        
        Args:
            manager_id: ID менеджера
            
        Returns:
            True если успешно
        """
        manager = ManagerService.get_manager_by_id(manager_id)
        if not manager:
            raise NotFoundError(f"Менеджер с ID {manager_id} не найден")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем использование
                cursor.execute('SELECT COUNT(*) FROM orders WHERE manager_id = ?', (manager_id,))
                count = cursor.fetchone()[0]
                if count > 0:
                    raise ValidationError(f"Менеджер используется в {count} заявках. Удаление невозможно.")
                
                # Получаем user_id перед удалением
                user_id = manager.get('user_id')
                custom_role_name = f'manager_{manager_id}'
                
                # Удаляем связанного пользователя и роль, если есть
                if user_id:
                    try:
                        from app.services.user_service import UserService
                        
                        # Сначала удаляем пользователя (физически)
                        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                        if cursor.rowcount > 0:
                            logger.info(f"Удален пользователь ID={user_id}, связанный с менеджером {manager_id}")
                        
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
                
                # Удаляем менеджера
                cursor.execute('DELETE FROM managers WHERE id = ?', (manager_id,))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении менеджера {manager_id}: {e}", exc_info=True)
            raise


