"""
Сервис для работы со статусами заявок.
"""
from typing import Dict, List, Optional, Any
from app.database.queries.status_queries import StatusQueries
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.error_handlers import handle_service_error
import logging

logger = logging.getLogger(__name__)


class StatusService:
    """Сервис для работы со статусами."""
    
    @staticmethod
    @handle_service_error
    def get_all_statuses(include_archived: bool = False) -> List[Dict[str, Any]]:
        """
        Получает все статусы.
        
        Args:
            include_archived: Включать архивные статусы
            
        Returns:
            Список статусов
        """
        return StatusQueries.get_all_statuses(include_archived=include_archived)
    
    @staticmethod
    @handle_service_error
    def get_status_by_id(status_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает статус по ID.
        
        Args:
            status_id: ID статуса
            
        Returns:
            Словарь с данными статуса или None
            
        Raises:
            NotFoundError: Если статус не найден
        """
        status = StatusQueries.get_status_by_id(status_id)
        if not status:
            raise NotFoundError(f"Статус с ID {status_id} не найден")
        return status
    
    @staticmethod
    @handle_service_error
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
        
        Args:
            name: Название статуса (обязательно)
            code: Код статуса (автогенерируется если не указан)
            color: Цвет статуса (hex)
            group_name: Группа статуса
            is_default: Является ли статусом по умолчанию
            sort_order: Порядок сортировки
            triggers_payment_modal: Вызывает окно оплаты (1 = да)
            accrues_salary: Начисляет зарплату (1 = да)
            is_archived: Архивный статус (1 = да)
            is_final: Финальный статус (1 = да)
            blocks_edit: Запрещает редактирование (1 = да)
            requires_warranty: Требует гарантию (1 = да)
            requires_comment: Требует комментарий (1 = да)
            client_name: Название для клиента
            client_description: Описание для клиента
            
        Returns:
            ID созданного статуса
            
        Raises:
            ValidationError: Если данные невалидны
        """
        if not name or not name.strip():
            raise ValidationError("Название статуса не может быть пустым")
        
        try:
            # Логируем перед передачей в запрос
            logger.info(f"StatusService.create_status: передаем group_name={repr(group_name)}, тип={type(group_name)}")
            return StatusQueries.create_status(
                name=name.strip(),
                code=code,
                color=color,
                group_name=group_name,
                is_default=is_default,
                sort_order=sort_order,
                triggers_payment_modal=triggers_payment_modal,
                accrues_salary=accrues_salary,
                is_archived=is_archived,
                is_final=is_final,
                blocks_edit=blocks_edit,
                requires_warranty=requires_warranty,
                requires_comment=requires_comment,
                client_name=client_name,
                client_description=client_description
            )
        except ValueError as e:
            # ValueError уже содержит понятное сообщение
            raise ValidationError(str(e))
        except Exception as e:
            logger.error(f"Ошибка при создании статуса: {e}", exc_info=True)
            # Преобразуем технические ошибки в понятные сообщения
            error_msg = str(e)
            if 'UNIQUE constraint failed' in error_msg and 'code' in error_msg:
                raise ValidationError("Статус с таким кодом уже существует. Пожалуйста, используйте другой код.")
            raise DatabaseError(f"Ошибка при создании статуса: {e}")
    
    @staticmethod
    @handle_service_error
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
        
        Args:
            status_id: ID статуса
            ... (остальные параметры как в create_status)
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если статус не найден
            ValidationError: Если данные невалидны
        """
        # Проверяем существование статуса
        status = StatusQueries.get_status_by_id(status_id)
        if not status:
            raise NotFoundError(f"Статус с ID {status_id} не найден")
        
        if name is not None and not name.strip():
            raise ValidationError("Название статуса не может быть пустым")
        
        try:
            return StatusQueries.update_status(
                status_id=status_id,
                name=name.strip() if name else None,
                color=color,
                group_name=group_name,
                sort_order=sort_order,
                is_default=is_default,
                triggers_payment_modal=triggers_payment_modal,
                accrues_salary=accrues_salary,
                is_archived=is_archived,
                is_final=is_final,
                blocks_edit=blocks_edit,
                requires_warranty=requires_warranty,
                requires_comment=requires_comment,
                client_name=client_name,
                client_description=client_description
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса {status_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при обновлении статуса: {e}")
    
    @staticmethod
    @handle_service_error
    def archive_status(status_id: int) -> bool:
        """
        Архивирует статус.
        
        Args:
            status_id: ID статуса
            
        Returns:
            True если успешно
        """
        return StatusService.update_status(status_id, is_archived=1)
    
    @staticmethod
    @handle_service_error
    def unarchive_status(status_id: int) -> bool:
        """
        Разархивирует статус.
        
        Args:
            status_id: ID статуса
            
        Returns:
            True если успешно
        """
        return StatusService.update_status(status_id, is_archived=0)
    
    @staticmethod
    @handle_service_error
    def delete_status(status_id: int) -> bool:
        """
        Удаляет статус (только если он не используется).
        
        Args:
            status_id: ID статуса
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если статус не найден
            ValidationError: Если статус используется
        """
        status = StatusQueries.get_status_by_id(status_id)
        if not status:
            raise NotFoundError(f"Статус с ID {status_id} не найден")
        
        try:
            return StatusQueries.delete_status(status_id)
        except ValueError as e:
            raise ValidationError(str(e))
        except Exception as e:
            logger.error(f"Ошибка при удалении статуса {status_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при удалении статуса: {e}")
    
    @staticmethod
    @handle_service_error
    def reorder_statuses(status_ids: List[int]) -> bool:
        """
        Изменяет порядок статусов.
        
        Args:
            status_ids: Список ID статусов в новом порядке
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если список пуст
        """
        if not status_ids:
            raise ValidationError("Список статусов не может быть пустым")
        
        try:
            return StatusQueries.reorder_statuses(status_ids)
        except Exception as e:
            logger.error(f"Ошибка при изменении порядка статусов: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при изменении порядка статусов: {e}")
    
    @staticmethod
    @handle_service_error
    def get_status_history(order_id: int) -> List[Dict[str, Any]]:
        """
        Получает историю смены статусов для заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список записей истории
        """
        return StatusQueries.get_status_history(order_id)


