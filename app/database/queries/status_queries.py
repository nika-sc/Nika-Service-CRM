"""
SQL запросы для работы со статусами заявок.
"""
from typing import Dict, List, Optional
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)


class StatusQueries:
    """Класс для SQL-запросов по статусам."""
    
    @staticmethod
    def get_all_statuses(include_archived: bool = False) -> List[Dict]:
        """
        Получает все статусы.
        
        Args:
            include_archived: Включать архивные статусы
            
        Returns:
            Список статусов
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                query = '''
                    SELECT 
                        id, code, name, color, group_name,
                        is_default, sort_order,
                        triggers_payment_modal, accrues_salary,
                        is_archived, is_final, blocks_edit,
                        requires_warranty, requires_comment,
                        client_name, client_description,
                        created_at
                    FROM order_statuses
                '''
                if not include_archived:
                    query += ' WHERE is_archived = 0 OR is_archived IS NULL'
                query += ' ORDER BY sort_order, name'
                
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении статусов: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_status_by_id(status_id: int) -> Optional[Dict]:
        """
        Получает статус по ID.
        
        Args:
            status_id: ID статуса
            
        Returns:
            Словарь с данными статуса или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        id, code, name, color, group_name,
                        is_default, sort_order,
                        triggers_payment_modal, accrues_salary,
                        is_archived, is_final, blocks_edit,
                        requires_warranty, requires_comment,
                        client_name, client_description,
                        created_at
                    FROM order_statuses
                    WHERE id = ?
                ''', (status_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении статуса {status_id}: {e}", exc_info=True)
            return None
    
    @staticmethod
    def create_status(
        name: str,
        code: Optional[str] = None,
        color: str = '#007bff',
        group_name: Optional[str] = None,
        is_default: int = 0,
        sort_order: int = 0,
        triggers_payment_modal: int = 0,
        accrues_salary: int = 0,
        is_archived: int = 0,
        is_final: int = 0,
        blocks_edit: int = 0,
        requires_warranty: int = 0,
        requires_comment: int = 0,
        client_name: Optional[str] = None,
        client_description: Optional[str] = None
    ) -> int:
        """
        Создает новый статус.
        
        Returns:
            ID созданного статуса
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Генерируем code если не указан
                if not code:
                    code = name.lower().replace(' ', '_').replace('-', '_')
                    # Проверяем уникальность кода и добавляем суффикс если нужно
                    original_code = code
                    counter = 1
                    while True:
                        cursor.execute('SELECT id FROM order_statuses WHERE code = ?', (code,))
                        if not cursor.fetchone():
                            break
                        code = f"{original_code}_{counter}"
                        counter += 1
                
                # Проверяем уникальность кода перед вставкой (если код был указан явно)
                if code:
                    cursor.execute('SELECT id, name FROM order_statuses WHERE code = ?', (code,))
                    existing = cursor.fetchone()
                    if existing:
                        existing_name = existing[1] if len(existing) > 1 else 'неизвестно'
                        raise ValueError(f"Статус с кодом '{code}' уже существует (статус: '{existing_name}'). Пожалуйста, используйте другой код.")
                
                # Если это статус по умолчанию, снимаем флаг с других статусов
                if is_default == 1:
                    cursor.execute('UPDATE order_statuses SET is_default = 0 WHERE is_default = 1')
                    logger.info(f"Снят флаг is_default со всех существующих статусов перед созданием нового статуса по умолчанию")
                
                # Логируем перед вставкой
                logger.info(f"StatusQueries.create_status: вставляем group_name={repr(group_name)}, тип={type(group_name)}")
                logger.info(f"StatusQueries.create_status: все параметры: code={code}, name={name}, color={color}, group_name={repr(group_name)}, is_default={is_default}")
                
                cursor.execute('''
                    INSERT INTO order_statuses (
                        code, name, color, group_name,
                        is_default, sort_order,
                        triggers_payment_modal, accrues_salary,
                        is_archived, is_final, blocks_edit,
                        requires_warranty, requires_comment,
                        client_name, client_description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code, name, color, group_name,
                    is_default, sort_order,
                    triggers_payment_modal, accrues_salary,
                    is_archived, is_final, blocks_edit,
                    requires_warranty, requires_comment,
                    client_name, client_description
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            error_msg = str(e)
            if 'UNIQUE constraint failed: order_statuses.code' in error_msg:
                # Пытаемся получить информацию о существующем статусе
                try:
                    cursor.execute('SELECT name FROM order_statuses WHERE code = ?', (code,))
                    existing = cursor.fetchone()
                    if existing:
                        existing_name = existing[0]
                        raise ValueError(f"Статус с кодом '{code}' уже существует (статус: '{existing_name}'). Пожалуйста, используйте другой код.")
                    else:
                        raise ValueError(f"Статус с кодом '{code}' уже существует. Пожалуйста, используйте другой код.")
                except ValueError:
                    raise
                except Exception:
                    raise ValueError(f"Статус с кодом '{code}' уже существует. Пожалуйста, используйте другой код.")
            else:
                logger.error(f"Ошибка БД при создании статуса: {e}", exc_info=True)
                raise ValueError(f"Ошибка базы данных: {error_msg}")
        except ValueError:
            raise  # Пробрасываем ValueError как есть
        except Exception as e:
            logger.error(f"Ошибка при создании статуса: {e}", exc_info=True)
            raise
    
    @staticmethod
    def update_status(
        status_id: int,
        name: Optional[str] = None,
        color: Optional[str] = None,
        group_name: Optional[str] = None,
        sort_order: Optional[int] = None,
        is_default: Optional[int] = None,
        triggers_payment_modal: Optional[int] = None,
        accrues_salary: Optional[int] = None,
        is_archived: Optional[int] = None,
        is_final: Optional[int] = None,
        blocks_edit: Optional[int] = None,
        requires_warranty: Optional[int] = None,
        requires_comment: Optional[int] = None,
        client_name: Optional[str] = None,
        client_description: Optional[str] = None
    ) -> bool:
        """
        Обновляет статус.
        
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if name is not None:
                    updates.append('name = ?')
                    params.append(name)
                if color is not None:
                    updates.append('color = ?')
                    params.append(color)
                if group_name is not None:
                    updates.append('group_name = ?')
                    params.append(group_name)
                if sort_order is not None:
                    updates.append('sort_order = ?')
                    params.append(sort_order)
                if is_default is not None:
                    # Если устанавливаем статус как "по умолчанию", снимаем флаг с других статусов
                    if is_default == 1:
                        cursor.execute('UPDATE order_statuses SET is_default = 0 WHERE is_default = 1 AND id != ?', (status_id,))
                        logger.info(f"Снят флаг is_default со всех других статусов перед установкой для статуса {status_id}")
                    updates.append('is_default = ?')
                    params.append(is_default)
                if triggers_payment_modal is not None:
                    updates.append('triggers_payment_modal = ?')
                    params.append(triggers_payment_modal)
                if accrues_salary is not None:
                    updates.append('accrues_salary = ?')
                    params.append(accrues_salary)
                if is_archived is not None:
                    updates.append('is_archived = ?')
                    params.append(is_archived)
                if is_final is not None:
                    updates.append('is_final = ?')
                    params.append(is_final)
                if blocks_edit is not None:
                    updates.append('blocks_edit = ?')
                    params.append(blocks_edit)
                if requires_warranty is not None:
                    updates.append('requires_warranty = ?')
                    params.append(requires_warranty)
                if requires_comment is not None:
                    updates.append('requires_comment = ?')
                    params.append(requires_comment)
                if client_name is not None:
                    updates.append('client_name = ?')
                    params.append(client_name)
                if client_description is not None:
                    updates.append('client_description = ?')
                    params.append(client_description)
                
                if not updates:
                    return False
                
                params.append(status_id)
                cursor.execute(
                    f'UPDATE order_statuses SET {", ".join(updates)} WHERE id = ?',
                    params
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса {status_id}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def delete_status(status_id: int) -> bool:
        """
        Удаляет статус (только если он не используется в заявках).
        
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем использование
                cursor.execute('SELECT COUNT(*) FROM orders WHERE status_id = ?', (status_id,))
                count = cursor.fetchone()[0]
                if count > 0:
                    raise ValueError(f"Статус используется в {count} заявках. Удаление невозможно.")
                
                cursor.execute('DELETE FROM order_statuses WHERE id = ?', (status_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении статуса {status_id}: {e}", exc_info=True)
            raise
    
    @staticmethod
    def reorder_statuses(status_ids: List[int]) -> bool:
        """
        Изменяет порядок статусов.
        
        Args:
            status_ids: Список ID статусов в новом порядке
            
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for idx, status_id in enumerate(status_ids, 1):
                    cursor.execute(
                        'UPDATE order_statuses SET sort_order = ? WHERE id = ?',
                        (idx, status_id)
                    )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при изменении порядка статусов: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_status_history(order_id: int) -> List[Dict]:
        """
        Получает историю смены статусов для заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список записей истории
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                # Проверяем структуру таблицы (может быть old_status_id/new_status_id или status_id)
                cursor.execute("PRAGMA table_info(order_status_history)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'new_status_id' in columns:
                    # Старая структура с old_status_id, new_status_id
                    cursor.execute('''
                        SELECT 
                            osh.id,
                            osh.order_id,
                            osh.new_status_id as status_id,
                            osh.changed_by as user_id,
                            osh.comment,
                            osh.created_at,
                            os.name as status_name,
                            os.color as status_color,
                            osh.changed_by_username as user_name
                        FROM order_status_history osh
                        LEFT JOIN order_statuses os ON os.id = osh.new_status_id
                        WHERE osh.order_id = ?
                        ORDER BY osh.created_at DESC
                    ''', (order_id,))
                else:
                    # Новая структура с status_id, user_id
                    cursor.execute('''
                        SELECT 
                            osh.id,
                            osh.order_id,
                            osh.status_id,
                            osh.user_id,
                            osh.comment,
                            osh.created_at,
                            os.name as status_name,
                            os.color as status_color,
                            u.username as user_name
                        FROM order_status_history osh
                        LEFT JOIN order_statuses os ON os.id = osh.status_id
                        LEFT JOIN users u ON u.id = osh.user_id
                        WHERE osh.order_id = ?
                        ORDER BY osh.created_at DESC
                    ''', (order_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении истории статусов для заявки {order_id}: {e}", exc_info=True)
            return []

