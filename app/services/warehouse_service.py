"""
Сервис для работы со складом.
"""
from typing import Optional, Dict, List, Any
from app.database.queries.warehouse_queries import WarehouseQueries
from app.utils.pagination import Paginator
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.database.connection import get_db_connection
from app.utils.error_handlers import handle_service_error
from app.services.action_log_service import ActionLogService
import sqlite3
import logging
from datetime import datetime
from app.utils.datetime_utils import get_moscow_now_str

logger = logging.getLogger(__name__)


class WarehouseService:
    """Сервис для работы со складом."""
    
    @staticmethod
    @handle_service_error
    def get_stock_levels(
        search_query: Optional[str] = None,
        category: Optional[str] = None,
        low_stock_only: bool = False,
        page: int = 1,
        per_page: int = 50,
        sort_by: str = 'name',
        sort_order: str = 'ASC'
    ) -> Paginator:
        """
        Получает остатки товаров на складе.
        
        Args:
            search_query: Поисковый запрос (полнотекстовый поиск по всем словам)
            category: Фильтр по категории
            low_stock_only: Только товары с низким остатком
            page: Номер страницы
            per_page: Количество элементов на странице
            sort_by: Поле для сортировки
            sort_order: Направление сортировки (ASC, DESC)
            
        Returns:
            Paginator с остатками товаров
        """
        result = WarehouseQueries.get_stock_levels(
            search_query=search_query,
            category=category,
            low_stock_only=low_stock_only,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return Paginator(
            items=result['items'],
            page=result['page'],
            per_page=result['per_page'],
            total=result['total']
        )
    
    @staticmethod
    @handle_service_error
    def get_low_stock_items() -> List[Dict]:
        """
        Получает товары с низким остатком.
        
        Returns:
            Список товаров с низким остатком
        """
        return WarehouseQueries.get_low_stock_items()
    
    @staticmethod
    @handle_service_error
    def create_purchase(
        supplier_id: Optional[int] = None,
        supplier_name: str = None,
        purchase_date: str = None,
        items: List[Dict] = None,
        user_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Создает закупку.
        
        Args:
            supplier_id: ID поставщика (приоритетнее, чем supplier_name)
            supplier_name: Название поставщика (используется если supplier_id не указан)
            purchase_date: Дата закупки (YYYY-MM-DD)
            items: Список позиций [{'part_id': int, 'quantity': int, 'purchase_price': float}]
            user_id: ID пользователя, создавшего закупку
            notes: Примечания
            
        Returns:
            ID созданной закупки
            
        Raises:
            ValidationError: Если данные невалидны
        """
        # Получаем название поставщика если передан только supplier_id
        if supplier_id and not supplier_name:
            supplier = WarehouseQueries.get_supplier_by_id(supplier_id)
            if not supplier:
                raise ValidationError(f"Поставщик с ID {supplier_id} не найден")
            supplier_name = supplier['name']
        
        if not supplier_name or not supplier_name.strip():
            raise ValidationError("Название поставщика обязательно")
        
        if not purchase_date:
            raise ValidationError("Дата закупки обязательна")
        
        if not items or len(items) == 0:
            raise ValidationError("Должна быть хотя бы одна позиция")
        
        # Валидация позиций
        total_amount = 0.0
        for item in items:
            if not item.get('part_id'):
                raise ValidationError("ID товара обязателен для каждой позиции")
            if not item.get('quantity') or item.get('quantity') <= 0:
                raise ValidationError("Количество должно быть больше 0")
            if not item.get('purchase_price') or item.get('purchase_price') < 0:
                raise ValidationError("Цена закупки должна быть неотрицательной")
            
            quantity = int(item['quantity'])
            purchase_price = float(item['purchase_price'])
            total_price = quantity * purchase_price
            total_amount += total_price
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Создание закупки
                cursor.execute('''
                    INSERT INTO purchases 
                    (supplier_id, supplier_name, purchase_date, total_amount, status, notes, created_by)
                    VALUES (?, ?, ?, ?, 'draft', ?, ?)
                ''', (supplier_id, supplier_name.strip(), purchase_date, total_amount, notes, user_id))
                
                purchase_id = cursor.lastrowid
                
                # Добавление позиций
                for item in items:
                    quantity = int(item['quantity'])
                    purchase_price = float(item['purchase_price'])
                    total_price = quantity * purchase_price
                    
                    cursor.execute('''
                        INSERT INTO purchase_items 
                        (purchase_id, part_id, quantity, purchase_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (purchase_id, item['part_id'], quantity, purchase_price, total_price))
                
                conn.commit()
                logger.info(f"Закупка {purchase_id} создана пользователем {user_id}")
                
                # Логируем создание закупки
                try:
                    from app.services.user_service import UserService
                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            username = user.get('username')
                    
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='create',
                        entity_type='purchase',
                        entity_id=purchase_id,
                        description=f"Создана закупка #{purchase_id} на сумму {total_amount:.2f} руб",
                        details={
                            'ID поставщика': supplier_id,
                            'Поставщик': supplier_name.strip() if supplier_name else None,
                            'Сумма': f"{total_amount:.2f} ₽",
                            'Позиций': len(items)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать создание закупки: {e}")
                
                return purchase_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при создании закупки: {e}")
            raise DatabaseError(f"Ошибка при создании закупки: {e}")
    
    @staticmethod
    @handle_service_error
    def complete_purchase(purchase_id: int, user_id: Optional[int] = None) -> bool:
        """
        Завершает закупку (обновляет остатки товаров).
        
        Args:
            purchase_id: ID закупки
            user_id: ID пользователя
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если закупка не найдена
            ValidationError: Если закупка уже завершена
        """
        purchase = WarehouseQueries.get_purchase_by_id(purchase_id)
        if not purchase:
            raise NotFoundError(f"Закупка с ID {purchase_id} не найдена")
        
        if purchase['status'] == 'completed':
            raise ValidationError("Закупка уже завершена")
        
        items = WarehouseQueries.get_purchase_items(purchase_id)
        if not items:
            raise ValidationError("Закупка не содержит позиций")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Обновляем остатки и создаем движения
                for item in items:
                    part_id = item['part_id']
                    quantity = item['quantity']
                    purchase_price = item['purchase_price']
                    
                    # Обновляем остаток
                    cursor.execute('''
                        UPDATE parts 
                        SET stock_quantity = stock_quantity + ?,
                            purchase_price = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (quantity, purchase_price, part_id))
                    
                    # Создаем движение
                    cursor.execute('''
                        INSERT INTO stock_movements 
                        (part_id, movement_type, quantity, reference_id, reference_type, created_by, notes)
                        VALUES (?, 'purchase', ?, ?, 'purchase', ?, ?)
                    ''', (part_id, quantity, purchase_id, user_id, f"Закупка #{purchase_id}"))
                
                # Обновляем статус закупки
                cursor.execute('''
                    UPDATE purchases 
                    SET status = 'completed',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (purchase_id,))
                
                conn.commit()
                logger.info(f"Закупка {purchase_id} завершена пользователем {user_id}")
                
                # Логируем завершение закупки
                try:
                    from app.services.action_log_service import ActionLogService
                    from app.services.user_service import UserService
                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            username = user.get('username')
                    
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='update',
                        entity_type='purchase',
                        entity_id=purchase_id,
                        description=f"Завершена закупка #{purchase_id}",
                        details={
                            'Статус': 'Завершена',
                            'Позиций': len(items),
                            'Сумма': f"{purchase.get('total_amount', 0):.2f} ₽"
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать завершение закупки: {e}")

                # Проверяем low_stock после изменения остатков.
                try:
                    from app.services.notification_service import NotificationService
                    for item in items:
                        NotificationService.notify_low_stock(int(item['part_id']))
                except Exception as e:
                    logger.debug(f"Low stock проверка после закупки пропущена: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при завершении закупки {purchase_id}: {e}")
            raise DatabaseError(f"Ошибка при завершении закупки: {e}")
    
    @staticmethod
    @handle_service_error
    def get_purchases(
        supplier_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Paginator:
        """
        Получает список закупок.
        
        Args:
            supplier_id: Фильтр по поставщику
            status: Фильтр по статусу
            date_from: Дата начала
            date_to: Дата окончания
            page: Номер страницы
            per_page: Количество элементов на странице
            
        Returns:
            Paginator с закупками
        """
        result = WarehouseQueries.get_purchases(
            supplier_id=supplier_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page
        )
        
        return Paginator(
            items=result['items'],
            page=result['page'],
            per_page=result['per_page'],
            total=result['total']
        )
    
    @staticmethod
    @handle_service_error
    def get_purchase_by_id(purchase_id: int) -> Optional[Dict]:
        """
        Получает закупку по ID.
        
        Args:
            purchase_id: ID закупки
            
        Returns:
            Словарь с данными закупки или None
        """
        purchase = WarehouseQueries.get_purchase_by_id(purchase_id)
        if purchase:
            purchase['items'] = WarehouseQueries.get_purchase_items(purchase_id)
        return purchase
    
    @staticmethod
    @handle_service_error
    def update_purchase(
        purchase_id: int,
        supplier_id: Optional[int] = None,
        supplier_name: str = None,
        purchase_date: str = None,
        items: List[Dict] = None,
        user_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Обновляет закупку (только для черновиков).
        
        Args:
            purchase_id: ID закупки
            supplier_id: ID поставщика (приоритетнее, чем supplier_name)
            supplier_name: Название поставщика (используется если supplier_id не указан)
            purchase_date: Дата закупки (YYYY-MM-DD)
            items: Список позиций [{'part_id': int, 'quantity': int, 'purchase_price': float}]
            user_id: ID пользователя
            notes: Примечания
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если закупка не найдена
            ValidationError: Если закупка уже завершена или данные невалидны
        """
        # Проверяем существование и статус закупки
        purchase = WarehouseQueries.get_purchase_by_id(purchase_id)
        if not purchase:
            raise NotFoundError(f"Закупка с ID {purchase_id} не найдена")
        
        if purchase['status'] != 'draft':
            raise ValidationError("Можно редактировать только черновики закупок")
        
        # Получаем название поставщика если передан только supplier_id
        if supplier_id and not supplier_name:
            supplier = WarehouseQueries.get_supplier_by_id(supplier_id)
            if not supplier:
                raise ValidationError(f"Поставщик с ID {supplier_id} не найден")
            supplier_name = supplier['name']
        
        # Валидация данных
        if not supplier_name or not supplier_name.strip():
            raise ValidationError("Название поставщика обязательно")
        
        if not purchase_date:
            raise ValidationError("Дата закупки обязательна")
        
        if not items or len(items) == 0:
            raise ValidationError("Должна быть хотя бы одна позиция")
        
        # Валидация позиций
        total_amount = 0.0
        for item in items:
            if not item.get('part_id'):
                raise ValidationError("ID товара обязателен для каждой позиции")
            if not item.get('quantity') or item.get('quantity') <= 0:
                raise ValidationError("Количество должно быть больше 0")
            if not item.get('purchase_price') or item.get('purchase_price') < 0:
                raise ValidationError("Цена закупки должна быть неотрицательной")
            
            quantity = int(item['quantity'])
            purchase_price = float(item['purchase_price'])
            total_price = quantity * purchase_price
            total_amount += total_price
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Обновление закупки
                cursor.execute('''
                    UPDATE purchases 
                    SET supplier_id = ?,
                        supplier_name = ?,
                        purchase_date = ?,
                        total_amount = ?,
                        notes = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'draft'
                ''', (supplier_id, supplier_name.strip(), purchase_date, total_amount, notes, purchase_id))
                
                if cursor.rowcount == 0:
                    raise ValidationError("Не удалось обновить закупку. Возможно, она уже завершена.")
                
                # Удаляем старые позиции
                cursor.execute('DELETE FROM purchase_items WHERE purchase_id = ?', (purchase_id,))
                
                # Добавляем новые позиции
                for item in items:
                    quantity = int(item['quantity'])
                    purchase_price = float(item['purchase_price'])
                    total_price = quantity * purchase_price
                    
                    cursor.execute('''
                        INSERT INTO purchase_items 
                        (purchase_id, part_id, quantity, purchase_price, total_price)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (purchase_id, item['part_id'], quantity, purchase_price, total_price))
                
                conn.commit()
                logger.info(f"Закупка {purchase_id} обновлена пользователем {user_id}")

                # Логируем обновление закупки
                try:
                    from app.services.user_service import UserService
                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            username = user.get('username')

                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='update',
                        entity_type='purchase',
                        entity_id=purchase_id,
                        description=f"Обновлена закупка #{purchase_id}",
                        details={
                            'ID поставщика': supplier_id,
                            'Поставщик': supplier_name.strip() if supplier_name else None,
                            'Сумма': f"{total_amount:.2f} ₽",
                            'Позиций': len(items)
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать обновление закупки {purchase_id}: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при обновлении закупки {purchase_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении закупки: {e}")
    
    @staticmethod
    @handle_service_error
    def delete_purchase(purchase_id: int, user_id: Optional[int] = None) -> bool:
        """
        Удаляет закупку (только черновики).
        
        Args:
            purchase_id: ID закупки
            user_id: ID пользователя
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если закупка не найдена
            ValidationError: Если закупка уже завершена
        """
        # Проверяем существование и статус закупки
        purchase = WarehouseQueries.get_purchase_by_id(purchase_id)
        if not purchase:
            raise NotFoundError(f"Закупка с ID {purchase_id} не найдена")
        
        if purchase['status'] != 'draft':
            raise ValidationError("Можно удалять только черновики закупок")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Удаляем позиции
                cursor.execute('DELETE FROM purchase_items WHERE purchase_id = ?', (purchase_id,))
                
                # Удаляем закупку
                cursor.execute('DELETE FROM purchases WHERE id = ? AND status = \'draft\'', (purchase_id,))
                
                if cursor.rowcount == 0:
                    raise ValidationError("Не удалось удалить закупку. Возможно, она уже завершена.")
                
                conn.commit()
                logger.info(f"Закупка {purchase_id} удалена пользователем {user_id}")

                # Логируем удаление закупки
                try:
                    from app.services.user_service import UserService
                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            username = user.get('username')

                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='delete',
                        entity_type='purchase',
                        entity_id=purchase_id,
                        description=f"Удалена закупка #{purchase_id}",
                        details={
                            'Поставщик': purchase.get('supplier_name', 'Неизвестен'),
                            'Сумма': f"{purchase.get('total_amount', 0):.2f} ₽",
                            'Статус': 'черновик'
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать удаление закупки {purchase_id}: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при удалении закупки {purchase_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении закупки: {e}")
    
    @staticmethod
    @handle_service_error
    def get_stock_movements(
        part_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        operation_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Получает движения товаров.
        
        Args:
            part_id: Фильтр по товару
            movement_type: Тип движения
            operation_type: Тип операции ('manual' для ручных, 'auto' для автоматических)
            date_from: Дата начала
            date_to: Дата окончания
            limit: Максимальное количество записей
            
        Returns:
            Список движений
        """
        return WarehouseQueries.get_stock_movements(
            part_id=part_id,
            movement_type=movement_type,
            operation_type=operation_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )
    
    @staticmethod
    @handle_service_error
    def adjust_stock(
        part_id: int,
        quantity: int,
        reason: str,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Корректирует остаток товара.
        
        Args:
            part_id: ID товара
            quantity: Изменение количества (может быть отрицательным)
            reason: Причина корректировки
            user_id: ID пользователя
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если товар не найден
        """
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID товара")
        
        if quantity == 0:
            raise ValidationError("Изменение количества не может быть нулевым")
        
        if not reason or not reason.strip():
            raise ValidationError("Причина корректировки обязательна")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование товара
                cursor.execute('SELECT id, stock_quantity FROM parts WHERE id = ? AND is_deleted = 0', (part_id,))
                part = cursor.fetchone()
                if not part:
                    raise NotFoundError(f"Товар с ID {part_id} не найден")
                
                current_stock = part[1]
                new_stock = current_stock + quantity
                
                if new_stock < 0:
                    raise ValidationError(f"Недостаточно товара на складе. Текущий остаток: {current_stock}")
                
                # Обновляем остаток
                cursor.execute('''
                    UPDATE parts 
                    SET stock_quantity = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_stock, part_id))
                
                # Создаем движение
                movement_type = 'adjustment_increase' if quantity > 0 else 'adjustment_decrease'
                cursor.execute('''
                    INSERT INTO stock_movements 
                    (part_id, movement_type, quantity, reference_type, created_by, notes)
                    VALUES (?, ?, ?, 'adjustment', ?, ?)
                ''', (part_id, movement_type, quantity, user_id, reason.strip()))
                
                conn.commit()
                logger.info(f"Остаток товара {part_id} скорректирован на {quantity} пользователем {user_id}")
                
                # Логируем корректировку остатка
                try:
                    from app.services.action_log_service import ActionLogService
                    from app.services.user_service import UserService
                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            username = user.get('username')
                    
                    part_info = WarehouseQueries.get_part_by_id(part_id)
                    adjustment_type = 'увеличение' if quantity > 0 else 'уменьшение'
                    
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='update',
                        entity_type='part',
                        entity_id=part_id,
                        description=f"Корректировка остатка товара: {adjustment_type} на {abs(quantity)} шт.",
                        details={
                            'Товар': part_info.get('name') if part_info else None,
                            'Артикул': part_info.get('part_number') if part_info else None,
                            'Изменение': f"{quantity:+d} шт.",
                            'Было': f"{current_stock} шт.",
                            'Стало': f"{new_stock} шт.",
                            'Причина': reason.strip()
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать корректировку остатка: {e}")

                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_low_stock(part_id)
                except Exception as e:
                    logger.debug(f"Low stock проверка после корректировки пропущена: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при корректировке остатка товара {part_id}: {e}")
            raise DatabaseError(f"Ошибка при корректировке остатка: {e}")
    
    @staticmethod
    @handle_service_error
    def record_sale(
        part_id: int,
        quantity: int,
        order_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Записывает продажу товара (списание со склада).
        
        Args:
            part_id: ID товара
            quantity: Количество
            order_id: ID заявки
            user_id: ID пользователя
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данных недостаточно
            NotFoundError: Если товар не найден
        """
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID товара")
        
        if not quantity or quantity <= 0:
            raise ValidationError("Количество должно быть больше 0")
        
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем остаток
                cursor.execute('SELECT id, stock_quantity FROM parts WHERE id = ? AND is_deleted = 0', (part_id,))
                part = cursor.fetchone()
                if not part:
                    raise NotFoundError(f"Товар с ID {part_id} не найден")
                
                current_stock = part[1]
                if current_stock < quantity:
                    raise ValidationError(
                        f"Недостаточно товара на складе. Текущий остаток: {current_stock}, требуется: {quantity}"
                    )
                
                # Обновляем остаток
                new_stock = current_stock - quantity
                cursor.execute('''
                    UPDATE parts 
                    SET stock_quantity = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_stock, part_id))
                
                # Создаем движение
                cursor.execute('''
                    INSERT INTO stock_movements 
                    (part_id, movement_type, quantity, reference_id, reference_type, created_by, notes)
                    VALUES (?, 'sale', ?, ?, 'order', ?, ?)
                ''', (part_id, -quantity, order_id, user_id, f"Продажа в заявке #{order_id}"))
                
                conn.commit()
                logger.info(f"Товар {part_id} списан со склада: {quantity} шт. (заявка {order_id})")

                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_low_stock(part_id)
                except Exception as e:
                    logger.debug(f"Low stock проверка после продажи пропущена: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при списании товара {part_id}: {e}")
            raise DatabaseError(f"Ошибка при списании товара: {e}")
    
    @staticmethod
    @handle_service_error
    def record_return(
        part_id: int,
        quantity: int,
        order_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Записывает возврат товара (возврат на склад).
        
        Args:
            part_id: ID товара
            quantity: Количество
            order_id: ID заявки
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID товара")
        
        if not quantity or quantity <= 0:
            raise ValidationError("Количество должно быть больше 0")
        
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существование товара
                cursor.execute('SELECT id FROM parts WHERE id = ? AND is_deleted = 0', (part_id,))
                if not cursor.fetchone():
                    raise NotFoundError(f"Товар с ID {part_id} не найден")
                
                # Обновляем остаток
                cursor.execute('''
                    UPDATE parts 
                    SET stock_quantity = stock_quantity + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (quantity, part_id))
                
                # Создаем движение
                cursor.execute('''
                    INSERT INTO stock_movements 
                    (part_id, movement_type, quantity, reference_id, reference_type, created_by, notes)
                    VALUES (?, 'return', ?, ?, 'order', ?, ?)
                ''', (part_id, quantity, order_id, user_id, f"Возврат из заявки #{order_id}"))
                
                conn.commit()
                logger.info(f"Товар {part_id} возвращен на склад: {quantity} шт. (заявка {order_id})")
                
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при возврате товара {part_id}: {e}")
            raise DatabaseError(f"Ошибка при возврате товара: {e}")
    
    # ========== Методы для работы с товарами ==========
    
    @staticmethod
    @handle_service_error
    def create_part(
        name: str,
        part_number: str,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        unit: str = 'шт',
        stock_quantity: int = 0,
        retail_price: float = 0.0,
        purchase_price: Optional[float] = None,
        warranty_days: Optional[int] = None,
        comment: Optional[str] = None,
        description: Optional[str] = None,
        min_quantity: int = 0,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None
    ) -> int:
        """
        Создает новый товар.
        
        Args:
            name: Название товара (обязательно)
            part_number: Артикул (обязательно)
            category: Категория
            unit: Единица измерения (по умолчанию 'шт')
            stock_quantity: Начальный остаток
            retail_price: Розничная цена (обязательно)
            purchase_price: Закупочная цена
            warranty_days: Гарантия в днях
            comment: Комментарий
            description: Описание
            min_quantity: Минимальное количество
            
        Returns:
            ID созданного товара
            
        Raises:
            ValidationError: Если данные невалидны
        """
        if not name or not name.strip():
            raise ValidationError("Название товара обязательно")
        
        if not part_number or not part_number.strip():
            raise ValidationError("Артикул обязателен")
        
        if retail_price < 0:
            raise ValidationError("Розничная цена не может быть отрицательной")
        
        if purchase_price is not None and purchase_price < 0:
            raise ValidationError("Закупочная цена не может быть отрицательной")
        
        if stock_quantity < 0:
            raise ValidationError("Количество не может быть отрицательным")
        
        # Проверка на дубликаты
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Обрабатываем NULL значения в part_number
                part_number_clean = part_number.strip() if part_number and part_number.strip() else None
                if part_number_clean:
                    cursor.execute('''
                        SELECT id, name, part_number 
                        FROM parts 
                        WHERE name = ? AND part_number = ? AND is_deleted = 0
                        LIMIT 1
                    ''', (name.strip(), part_number_clean))
                else:
                    cursor.execute('''
                        SELECT id, name, part_number 
                        FROM parts 
                        WHERE name = ? AND (part_number IS NULL OR part_number = '') AND is_deleted = 0
                        LIMIT 1
                    ''', (name.strip(),))
                existing = cursor.fetchone()
                if existing:
                    existing_part_number = existing[2] or '(без артикула)'
                    raise ValidationError(
                        f"Товар с названием «{name.strip()}» и артикулом «{part_number_clean or '(без артикула)'}» уже существует "
                        f"(ID: {existing[0]}). Используйте существующий товар или измените название/артикул."
                    )
        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"Ошибка при проверке дубликатов товара: {e}")
            # Продолжаем создание, если проверка не удалась
        
        try:
            part_id = WarehouseQueries.create_part(
                name=name.strip(),
                part_number=part_number.strip(),
                category=category,
                category_id=category_id,
                unit=unit,
                stock_quantity=stock_quantity,
                retail_price=retail_price,
                purchase_price=purchase_price,
                warranty_days=warranty_days,
                comment=comment,
                description=description,
                min_quantity=min_quantity,
                salary_rule_type=salary_rule_type,
                salary_rule_value=salary_rule_value
            )
            
            # Если указан начальный остаток, создаем движение типа "income"
            if stock_quantity > 0:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO stock_movements 
                            (part_id, movement_type, quantity, reference_type, notes)
                            VALUES (?, 'income', ?, 'manual', ?)
                        ''', (part_id, stock_quantity, f"Начальный остаток при создании товара"))
                        conn.commit()
                        logger.info(f"Создано движение для начального остатка товара {part_id}: {stock_quantity} шт.")
                except Exception as e:
                    logger.warning(f"Не удалось создать движение для начального остатка товара {part_id}: {e}")
                    # Не прерываем создание товара, если не удалось создать движение
            
            # Логирование создания товара
            try:
                from flask_login import current_user
                user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
            except (AttributeError, RuntimeError):
                user_id = None
            
            WarehouseService._log_operation(
                operation_type='create',
                part_id=part_id,
                part_name=name.strip(),
                part_number=part_number.strip() if part_number else None,
                user_id=user_id,
                quantity=stock_quantity if stock_quantity > 0 else None,
                notes=f"Создан товар: {name.strip()}"
            )
            
            return part_id
        except sqlite3.IntegrityError as e:
            logger.error(f"Ошибка при создании товара: {e}")
            raise ValidationError("Товар с таким артикулом уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании товара: {e}")
            raise DatabaseError(f"Ошибка при создании товара: {e}")
    
    @staticmethod
    @handle_service_error
    def update_part(
        part_id: int,
        name: Optional[str] = None,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        unit: Optional[str] = None,
        stock_quantity: Optional[int] = None,
        retail_price: Optional[float] = None,
        purchase_price: Optional[float] = None,
        warranty_days: Optional[int] = None,
        comment: Optional[str] = None,
        description: Optional[str] = None,
        min_quantity: Optional[int] = None,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None
    ) -> bool:
        """
        Обновляет товар (кроме артикула).
        
        Args:
            part_id: ID товара
            name: Название
            category: Категория
            unit: Единица измерения
            stock_quantity: Остаток
            retail_price: Розничная цена
            purchase_price: Закупочная цена
            warranty_days: Гарантия в днях
            comment: Комментарий
            description: Описание
            min_quantity: Минимальное количество
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если товар не найден
            ValidationError: Если данные невалидны
        """
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID товара")
        
        # Проверяем существование товара
        part = WarehouseQueries.get_part_by_id(part_id)
        if not part:
            raise NotFoundError(f"Товар с ID {part_id} не найден")
        
        # Валидация данных
        if name is not None and not name.strip():
            raise ValidationError("Название товара не может быть пустым")
        
        if retail_price is not None and retail_price < 0:
            raise ValidationError("Розничная цена не может быть отрицательной")
        
        if purchase_price is not None and purchase_price < 0:
            raise ValidationError("Закупочная цена не может быть отрицательной")
        
        if stock_quantity is not None and stock_quantity < 0:
            raise ValidationError("Количество не может быть отрицательным")
        
        try:
            # Если изменяется stock_quantity, нужно создать движение
            old_stock = None
            if stock_quantity is not None:
                old_stock = part.get('stock_quantity', 0) or 0
                old_stock = int(old_stock)
            
            result = WarehouseQueries.update_part(
                part_id=part_id,
                name=name,
                category=category,
                category_id=category_id,
                unit=unit,
                stock_quantity=stock_quantity,
                retail_price=retail_price,
                purchase_price=purchase_price,
                warranty_days=warranty_days,
                comment=comment,
                description=description,
                min_quantity=min_quantity,
                salary_rule_type=salary_rule_type,
                salary_rule_value=salary_rule_value
            )
            
            # Создаем движение при изменении остатка
            if result and stock_quantity is not None and old_stock is not None:
                stock_diff = stock_quantity - old_stock
                if stock_diff != 0:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        movement_type = 'adjustment_increase' if stock_diff > 0 else 'adjustment_decrease'
                        movement_qty = abs(stock_diff)
                        notes = f"Корректировка остатка: было {old_stock}, стало {stock_quantity}"
                        
                        cursor.execute('''
                            INSERT INTO stock_movements 
                            (part_id, movement_type, quantity, reference_type, notes)
                            VALUES (?, ?, ?, 'adjustment', ?)
                        ''', (part_id, movement_type, movement_qty, notes))
                        conn.commit()
                        logger.info(f"Создано движение корректировки для товара {part_id}: {movement_qty} шт. (тип: {movement_type})")

            if result:
                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_low_stock(part_id)
                except Exception as e:
                    logger.debug(f"Low stock проверка после обновления товара пропущена: {e}")
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при обновлении товара {part_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении товара: {e}")
    
    @staticmethod
    @handle_service_error
    def delete_part(part_id: int) -> bool:
        """
        Мягкое удаление товара.
        
        Args:
            part_id: ID товара
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если товар не найден
        """
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID товара")
        
        part = WarehouseQueries.get_part_by_id(part_id)
        if not part:
            raise NotFoundError(f"Товар с ID {part_id} не найден")
        
        try:
            result = WarehouseQueries.delete_part(part_id)
            
            # Логирование удаления товара
            try:
                from flask_login import current_user
                user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
            except (AttributeError, RuntimeError):
                user_id = None
            
            WarehouseService._log_operation(
                operation_type='delete',
                part_id=part_id,
                part_name=part.get('name'),
                part_number=part.get('part_number'),
                user_id=user_id,
                notes=f"Удален товар: {part.get('name')}"
            )
            
            return result
        except Exception as e:
            logger.error(f"Ошибка при удалении товара {part_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении товара: {e}")
    
    @staticmethod
    @handle_service_error
    def restore_part(part_id: int) -> bool:
        """
        Восстанавливает удаленный товар.
        
        Args:
            part_id: ID товара
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если товар не найден
        """
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID товара")
        
        part = WarehouseQueries.get_part_by_id(part_id, include_deleted=True)
        if not part:
            raise NotFoundError(f"Товар с ID {part_id} не найден")
        
        try:
            return WarehouseQueries.restore_part(part_id)
        except Exception as e:
            logger.error(f"Ошибка при восстановлении товара {part_id}: {e}")
            raise DatabaseError(f"Ошибка при восстановлении товара: {e}")
    
    @staticmethod
    @handle_service_error
    def get_part_by_id(part_id: int, include_deleted: bool = False) -> Optional[Dict]:
        """
        Получает товар по ID.
        
        Args:
            part_id: ID товара
            include_deleted: Включать удаленные товары
            
        Returns:
            Словарь с данными товара или None
        """
        return WarehouseQueries.get_part_by_id(part_id, include_deleted=include_deleted)
    
    # ========== Методы для работы с категориями ==========
    
    @staticmethod
    @handle_service_error
    def get_categories() -> List[Dict]:
        """
        Получает список всех категорий товаров с иерархией.
        
        Returns:
            Список категорий с полем children для подкатегорий
        """
        return WarehouseQueries.get_categories()
    
    @staticmethod
    @handle_service_error
    def get_all_categories_flat() -> List[Dict]:
        """
        Получает плоский список всех категорий (без иерархии).
        
        Returns:
            Список всех категорий
        """
        return WarehouseQueries.get_all_categories_flat()
    
    @staticmethod
    @handle_service_error
    def create_category(name: str, description: Optional[str] = None, parent_id: Optional[int] = None) -> int:
        """
        Создает новую категорию товаров.
        
        Args:
            name: Название категории (обязательно)
            description: Описание категории
            parent_id: ID родительской категории (для подкатегорий)
            
        Returns:
            ID созданной категории
            
        Raises:
            ValidationError: Если данные невалидны
        """
        if not name or not name.strip():
            raise ValidationError("Название категории обязательно")
        
        try:
            category_id = WarehouseQueries.create_category(name.strip(), description.strip() if description else None, parent_id)
            
            # Логирование создания категории
            try:
                from flask_login import current_user
                user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
            except (AttributeError, RuntimeError):
                user_id = None
            
            WarehouseService._log_operation(
                operation_type='category_create',
                category_id=category_id,
                part_name=name.strip(),  # Используем part_name для отображения названия категории
                user_id=user_id,
                notes=f"Создана категория: {name.strip()}" + (f" (подкатегория категории ID {parent_id})" if parent_id else "")
            )
            
            return category_id
        except sqlite3.IntegrityError as e:
            logger.error(f"Ошибка при создании категории: {e}")
            raise ValidationError("Категория с таким названием уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании категории: {e}")
            raise DatabaseError(f"Ошибка при создании категории: {e}")
    
    @staticmethod
    @handle_service_error
    def update_category(category_id: int, name: str, description: Optional[str] = None, parent_id: Optional[int] = None) -> bool:
        """
        Обновляет категорию товаров.
        
        Args:
            category_id: ID категории
            name: Новое название (обязательно)
            description: Новое описание
            parent_id: ID родительской категории (None для корневых категорий)
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если категория не найдена
            ValidationError: Если данные невалидны
        """
        if not category_id or category_id <= 0:
            raise ValidationError("Неверный ID категории")
        
        if not name or not name.strip():
            raise ValidationError("Название категории обязательно")
        
        try:
            # Получаем старые данные категории для логирования
            old_category = WarehouseQueries.get_category_by_id(category_id)
            if not old_category:
                raise NotFoundError(f"Категория с ID {category_id} не найдена")
            
            old_name = old_category.get('name', '')
            old_description = old_category.get('description', '')
            old_parent_id = old_category.get('parent_id')
            
            result = WarehouseQueries.update_category(category_id, name.strip(), description.strip() if description else None, parent_id)
            if not result:
                raise NotFoundError(f"Категория с ID {category_id} не найдена")
            
            # Логирование обновления категории
            try:
                from flask_login import current_user
                user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
            except (AttributeError, RuntimeError):
                user_id = None
            
            changes = []
            if old_name != name.strip():
                changes.append(f"Название: '{old_name}' → '{name.strip()}'")
            if old_description != (description.strip() if description else ''):
                changes.append(f"Описание: '{old_description}' → '{description.strip() if description else ''}'")
            if old_parent_id != parent_id:
                changes.append(f"Родитель: {old_parent_id} → {parent_id}")
            
            WarehouseService._log_operation(
                operation_type='category_update',
                category_id=category_id,
                part_name=name.strip(),  # Используем part_name для отображения названия категории
                user_id=user_id,
                old_value=old_name,
                new_value=name.strip(),
                notes=f"Обновлена категория: {', '.join(changes) if changes else 'Без изменений'}"
            )
            
            return result
        except ValueError as e:
            logger.error(f"Ошибка при обновлении категории: {e}")
            raise ValidationError(str(e))
        except sqlite3.IntegrityError as e:
            logger.error(f"Ошибка при обновлении категории: {e}")
            raise ValidationError("Категория с таким названием уже существует")
        except Exception as e:
            logger.error(f"Ошибка при обновлении категории: {e}")
            raise DatabaseError(f"Ошибка при обновлении категории: {e}")
    
    @staticmethod
    @handle_service_error
    def delete_category(category_id: int) -> bool:
        """
        Удаляет категорию товаров.
        
        Args:
            category_id: ID категории
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если категория не найдена
        """
        if not category_id or category_id <= 0:
            raise ValidationError("Неверный ID категории")
        
        try:
            # Получаем данные категории перед удалением для логирования и проверки
            category = WarehouseQueries.get_category_by_id(category_id)
            if not category:
                raise NotFoundError(f"Категория с ID {category_id} не найдена")
            
            category_name = category.get('name', '')
            
            # Проверяем, есть ли товары в этой категории
            parts_count = WarehouseQueries.count_parts_in_category(category_name)
            if parts_count > 0:
                raise ValidationError(
                    f"Невозможно удалить категорию '{category_name}': в ней находится {parts_count} товар(ов). "
                    f"Сначала переместите товары в другую категорию или удалите их."
                )
            
            # Проверяем, есть ли подкатегории
            subcategories_count = WarehouseQueries.count_subcategories(category_id)
            if subcategories_count > 0:
                raise ValidationError(
                    f"Невозможно удалить категорию '{category_name}': у неё есть {subcategories_count} подкатегори(й). "
                    f"Сначала удалите или переместите подкатегории."
                )
            
            # Удаляем категорию
            result = WarehouseQueries.delete_category(category_id)
            if not result:
                raise NotFoundError(f"Категория с ID {category_id} не найдена")
            
            # Логирование удаления категории
            try:
                from flask_login import current_user
                user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
            except (AttributeError, RuntimeError):
                user_id = None
            
            WarehouseService._log_operation(
                operation_type='category_delete',
                category_id=category_id,
                part_name=category_name,  # Используем part_name для отображения названия категории
                user_id=user_id,
                notes=f"Удалена категория: {category_name}"
            )
            
            return result
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Ошибка при удалении категории: {e}")
            raise DatabaseError(f"Ошибка при удалении категории: {e}")
    
    # ========== Методы для прихода/расхода товаров ==========
    
    @staticmethod
    @handle_service_error
    def add_part_income(
        part_id: int,
        quantity: int,
        purchase_price: Optional[float] = None,
        notes: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Приход товара на склад.
        
        Args:
            part_id: ID товара
            quantity: Количество
            purchase_price: Новая себестоимость (если указана, обновляет глобально)
            notes: Примечание
            user_id: ID пользователя
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если товар не найден
            ValidationError: Если данные невалидны
        """
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID товара")
        
        if not quantity or quantity <= 0:
            raise ValidationError("Количество должно быть больше 0")
        
        if purchase_price is not None and purchase_price < 0:
            raise ValidationError("Себестоимость не может быть отрицательной")
        
        # Проверяем существование товара
        part = WarehouseQueries.get_part_by_id(part_id)
        if not part:
            raise NotFoundError(f"Товар с ID {part_id} не найден")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Обновляем остаток
                cursor.execute('''
                    UPDATE parts 
                    SET stock_quantity = stock_quantity + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (quantity, part_id))
                
                # Обновляем себестоимость, если указана
                if purchase_price is not None:
                    cursor.execute('''
                        UPDATE parts 
                        SET purchase_price = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (purchase_price, part_id))
                    logger.info(f"Себестоимость товара {part_id} обновлена на {purchase_price}")
                
                # Создаем движение
                cursor.execute('''
                    INSERT INTO stock_movements 
                    (part_id, movement_type, quantity, reference_type, created_by, notes)
                    VALUES (?, 'income', ?, 'manual', ?, ?)
                ''', (part_id, quantity, user_id, notes or f"Приход товара: {quantity} шт."))
                
                conn.commit()
                logger.info(f"Приход товара {part_id}: {quantity} шт.")
                
                # Логирование операции
                WarehouseService._log_operation(
                    operation_type='income',
                    part_id=part_id,
                    part_name=part.get('name'),
                    part_number=part.get('part_number'),
                    user_id=user_id,
                    quantity=quantity,
                    old_value=str(part.get('stock_quantity', 0)),
                    new_value=str(part.get('stock_quantity', 0) + quantity),
                    notes=notes or f"Приход товара: {quantity} шт."
                )
                
                # Логируем в action_logs
                try:
                    from app.services.action_log_service import ActionLogService
                    from app.services.user_service import UserService
                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            username = user.get('username')
                    
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='create',
                        entity_type='stock_movement',
                        entity_id=None,
                        description=f"Приход товара «{part.get('name')}»: {quantity} шт.",
                        details={
                            'ID товара': part_id,
                            'Товар': part.get('name'),
                            'Артикул': part.get('part_number'),
                            'Количество': f"{quantity} шт.",
                            'Тип движения': 'Приход',
                            'Примечание': notes
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать приход товара в action_logs: {e}")
                
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при приходе товара {part_id}: {e}")
            raise DatabaseError(f"Ошибка при приходе товара: {e}")
    
    @staticmethod
    @handle_service_error
    def add_part_expense(
        part_id: int,
        quantity: int,
        reason: str,
        notes: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Расход товара со склада.
        
        Args:
            part_id: ID товара
            quantity: Количество
            reason: Причина расхода
            notes: Примечание
            user_id: ID пользователя
            
        Returns:
            True если успешно
            
        Raises:
            NotFoundError: Если товар не найден
            ValidationError: Если данные невалидны или недостаточно товара на складе
        """
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID товара")
        
        if not quantity or quantity <= 0:
            raise ValidationError("Количество должно быть больше 0")
        
        if not reason or not reason.strip():
            raise ValidationError("Причина расхода обязательна")
        
        # Проверяем существование товара
        part = WarehouseQueries.get_part_by_id(part_id)
        if not part:
            raise NotFoundError(f"Товар с ID {part_id} не найден")
        
        # Проверяем остаток
        current_stock = part.get('stock_quantity', 0)
        if current_stock < quantity:
            raise ValidationError(f"Недостаточно товара на складе. Доступно: {current_stock}, требуется: {quantity}")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Уменьшаем остаток
                cursor.execute('''
                    UPDATE parts 
                    SET stock_quantity = stock_quantity - ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (quantity, part_id))
                
                # Создаем движение
                movement_notes = f"{reason}"
                if notes:
                    movement_notes += f". {notes}"
                
                cursor.execute('''
                    INSERT INTO stock_movements 
                    (part_id, movement_type, quantity, reference_type, created_by, notes)
                    VALUES (?, 'expense', ?, 'manual', ?, ?)
                ''', (part_id, quantity, user_id, movement_notes))
                
                conn.commit()
                logger.info(f"Расход товара {part_id}: {quantity} шт. Причина: {reason}")
                
                # Логирование операции
                WarehouseService._log_operation(
                    operation_type='expense',
                    part_id=part_id,
                    part_name=part.get('name'),
                    part_number=part.get('part_number'),
                    user_id=user_id,
                    quantity=quantity,
                    notes=movement_notes
                )
                
                # Логируем в action_logs
                try:
                    from app.services.action_log_service import ActionLogService
                    from app.services.user_service import UserService
                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            username = user.get('username')
                    
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='create',
                        entity_type='stock_movement',
                        entity_id=None,
                        description=f"Расход товара «{part.get('name')}»: {quantity} шт. ({reason})",
                        details={
                            'ID товара': part_id,
                            'Товар': part.get('name'),
                            'Артикул': part.get('part_number'),
                            'Количество': f"{quantity} шт.",
                            'Тип движения': 'Расход',
                            'Причина': reason,
                            'Примечание': notes
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать расход товара в action_logs: {e}")

                try:
                    from app.services.notification_service import NotificationService
                    NotificationService.notify_low_stock(part_id)
                except Exception as e:
                    logger.debug(f"Low stock проверка после расхода пропущена: {e}")

                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при расходе товара {part_id}: {e}")
            raise DatabaseError(f"Ошибка при расходе товара: {e}")
    
    # ========== Методы для логирования ==========
    
    @staticmethod
    def _log_operation(
        operation_type: str,
        part_id: Optional[int] = None,
        category_id: Optional[int] = None,
        part_name: Optional[str] = None,
        part_number: Optional[str] = None,
        category_name: Optional[str] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        quantity: Optional[int] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Логирует операцию со складом.
        
        Args:
            operation_type: Тип операции (create, delete, income, expense, category_create, category_update, category_delete)
            part_id: ID товара
            category_id: ID категории
            part_name: Название товара
            part_number: Артикул товара
            category_name: Название категории
            user_id: ID пользователя
            username: Имя пользователя
            quantity: Количество
            old_value: Старое значение (для изменений)
            new_value: Новое значение (для изменений)
            notes: Примечания
            ip_address: IP адрес
        """
        try:
            # Получаем IP адрес из request, если доступен
            if ip_address is None:
                try:
                    from flask import has_request_context, request
                    if has_request_context():
                        ip_address = request.remote_addr
                    else:
                        ip_address = None
                except Exception:
                    ip_address = None
            
            # Получаем username, если не указан
            if username is None and user_id:
                try:
                    from app.database.queries.user_queries import UserQueries
                    user = UserQueries.get_user_by_id(user_id)
                    if user:
                        username = user.get('username')
                except Exception:
                    pass
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO warehouse_logs 
                    (operation_type, part_id, category_id, part_name, part_number, user_id, username, 
                     quantity, old_value, new_value, notes, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (operation_type, part_id, category_id, part_name, part_number, user_id, username,
                      quantity, old_value, new_value, notes, ip_address))
                conn.commit()
        except Exception as e:
            # Не прерываем основную операцию, если логирование не удалось
            logger.warning(f"Не удалось залогировать операцию {operation_type}: {e}")
    
    @staticmethod
    @handle_service_error
    def get_warehouse_logs(
        operation_type: Optional[str] = None,
        part_id: Optional[int] = None,
        category_id: Optional[int] = None,
        user_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Paginator:
        """
        Получает логи операций со складом.
        
        Args:
            operation_type: Фильтр по типу операции (create, delete, income, expense, category_create, category_update, category_delete)
            part_id: Фильтр по товару
            category_id: Фильтр по категории
            user_id: Фильтр по пользователю
            date_from: Дата начала
            date_to: Дата окончания
            page: Номер страницы
            per_page: Количество элементов на странице
            
        Returns:
            Paginator с логами
        """
        result = WarehouseQueries.get_warehouse_logs(
            operation_type=operation_type,
            part_id=part_id,
            category_id=category_id,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            per_page=per_page
        )
        
        return Paginator(
            items=result['items'],
            page=result['page'],
            per_page=result['per_page'],
            total=result['total']
        )

    # ===========================================
    # ПОСТАВЩИКИ
    # ===========================================
    
    @staticmethod
    @handle_service_error
    def get_all_suppliers(include_inactive: bool = False) -> List[Dict]:
        """Получает всех поставщиков."""
        return WarehouseQueries.get_all_suppliers(include_inactive=include_inactive)
    
    @staticmethod
    @handle_service_error
    def get_supplier_by_id(supplier_id: int) -> Optional[Dict]:
        """Получает поставщика по ID."""
        supplier = WarehouseQueries.get_supplier_by_id(supplier_id)
        if not supplier:
            raise NotFoundError(f"Поставщик с ID {supplier_id} не найден")
        return supplier
    
    @staticmethod
    @handle_service_error
    def create_supplier(
        name: str,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        inn: Optional[str] = None,
        comment: Optional[str] = None
    ) -> int:
        """Создает нового поставщика."""
        if not name or not name.strip():
            raise ValidationError("Название поставщика обязательно")
        
        try:
            supplier_id = WarehouseQueries.create_supplier(
                name=name.strip(),
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                inn=inn,
                comment=comment
            )
            logger.info(f"Создан поставщик {supplier_id}: {name}")
            return supplier_id
        except ValueError as e:
            raise ValidationError(str(e))
    
    @staticmethod
    @handle_service_error
    def update_supplier(
        supplier_id: int,
        name: str,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        inn: Optional[str] = None,
        comment: Optional[str] = None,
        is_active: bool = True
    ) -> bool:
        """Обновляет поставщика."""
        if not name or not name.strip():
            raise ValidationError("Название поставщика обязательно")
        
        supplier = WarehouseQueries.get_supplier_by_id(supplier_id)
        if not supplier:
            raise NotFoundError(f"Поставщик с ID {supplier_id} не найден")
        
        try:
            result = WarehouseQueries.update_supplier(
                supplier_id=supplier_id,
                name=name.strip(),
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                inn=inn,
                comment=comment,
                is_active=is_active
            )
            logger.info(f"Обновлен поставщик {supplier_id}: {name}")
            return result
        except ValueError as e:
            raise ValidationError(str(e))
    
    @staticmethod
    @handle_service_error
    def delete_supplier(supplier_id: int) -> bool:
        """Удаляет поставщика (мягкое удаление)."""
        supplier = WarehouseQueries.get_supplier_by_id(supplier_id)
        if not supplier:
            raise NotFoundError(f"Поставщик с ID {supplier_id} не найден")
        
        result = WarehouseQueries.delete_supplier(supplier_id)
        logger.info(f"Удален поставщик {supplier_id}")
        return result
    
    # ===========================================
    # ИНВЕНТАРИЗАЦИЯ
    # ===========================================
    
    @staticmethod
    @handle_service_error
    def get_all_inventories(
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Получает все инвентаризационные ведомости."""
        return WarehouseQueries.get_all_inventories(
            status=status,
            date_from=date_from,
            date_to=date_to,
            limit=limit
        )
    
    @staticmethod
    @handle_service_error
    def get_inventory_by_id(inventory_id: int) -> Optional[Dict]:
        """Получает инвентаризацию по ID."""
        inventory = WarehouseQueries.get_inventory_by_id(inventory_id)
        if not inventory:
            raise NotFoundError(f"Инвентаризация с ID {inventory_id} не найдена")
        return inventory
    
    @staticmethod
    @handle_service_error
    def create_inventory(
        name: str,
        inventory_date: str,
        items: List[Dict],
        notes: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> int:
        """Создает новую инвентаризационную ведомость."""
        if not name or not name.strip():
            raise ValidationError("Название инвентаризации обязательно")
        
        if not inventory_date:
            raise ValidationError("Дата инвентаризации обязательна")
        
        if not items:
            raise ValidationError("Добавьте хотя бы одну позицию")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                inventory_id = WarehouseQueries.create_inventory(
                    name=name.strip(),
                    inventory_date=inventory_date,
                    notes=notes,
                    created_by=user_id
                )
                
                for item in items:
                    part_id = int(item['part_id'])
                    actual_quantity = int(item['actual_quantity'])
                    
                    cursor.execute('SELECT stock_quantity FROM parts WHERE id = ? AND is_deleted = 0', (part_id,))
                    part = cursor.fetchone()
                    if not part:
                        raise NotFoundError(f"Товар с ID {part_id} не найден")
                    
                    stock_quantity = part[0]
                    
                    WarehouseQueries.add_inventory_item(
                        inventory_id=inventory_id,
                        part_id=part_id,
                        stock_quantity=stock_quantity,
                        actual_quantity=actual_quantity,
                        notes=item.get('notes')
                    )
                
                conn.commit()
                logger.info(f"Создана инвентаризация {inventory_id}: {name}")
                return inventory_id
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Ошибка при создании инвентаризации: {e}")
            raise DatabaseError(f"Ошибка при создании инвентаризации: {e}")
    
    @staticmethod
    @handle_service_error
    def complete_inventory(inventory_id: int, user_id: Optional[int] = None) -> bool:
        """Завершает инвентаризацию (применяет корректировки остатков)."""
        inventory = WarehouseQueries.get_inventory_by_id(inventory_id)
        if not inventory:
            raise NotFoundError(f"Инвентаризация с ID {inventory_id} не найдена")
        
        if inventory['status'] == 'completed':
            raise ValidationError("Инвентаризация уже завершена")
        
        items = inventory.get('items', [])
        if not items:
            raise ValidationError("Инвентаризация не содержит позиций")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                from datetime import datetime
                from app.services.user_service import UserService
                
                username = None
                if user_id:
                    user = UserService.get_user_by_id(user_id)
                    if user:
                        username = user.get('username')
                
                for item in items:
                    part_id = item['part_id']
                    difference = item['difference']
                    
                    if difference == 0:
                        continue
                    
                    cursor.execute('SELECT stock_quantity FROM parts WHERE id = ? AND is_deleted = 0', (part_id,))
                    old_stock_result = cursor.fetchone()
                    old_stock = old_stock_result[0] if old_stock_result else 0
                    new_stock = old_stock + difference
                    
                    cursor.execute('''
                        UPDATE parts 
                        SET stock_quantity = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_stock, part_id))
                    
                    movement_type = 'adjustment_increase' if difference > 0 else 'adjustment_decrease'
                    cursor.execute('''
                        INSERT INTO stock_movements 
                        (part_id, movement_type, quantity, reference_type, reference_id, created_by, notes)
                        VALUES (?, ?, ?, 'adjustment', ?, ?, ?)
                    ''', (
                        part_id, 
                        movement_type,
                        abs(difference),
                        'adjustment',
                        inventory_id,
                        user_id, 
                        f"Инвентаризация #{inventory_id}: разница {difference:+d}"
                    ))
                    
                    part_name = item.get('part_name', f'Товар #{part_id}')
                    part_number = item.get('part_number', '')
                    
                    cursor.execute('''
                        INSERT INTO warehouse_logs 
                        (operation_type, part_id, part_name, part_number, user_id, username, 
                         quantity, old_value, new_value, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        'inventory_adjustment',
                        part_id,
                        part_name,
                        part_number,
                        user_id,
                        username,
                        abs(difference),
                        str(old_stock),
                        str(new_stock),
                        f"Инвентаризация #{inventory_id}"
                    ))
                
                WarehouseQueries.update_inventory_status(
                    inventory_id=inventory_id,
                    status='completed',
                    completed_at=get_moscow_now_str()
                )
                
                conn.commit()
                logger.info(f"Инвентаризация {inventory_id} завершена пользователем {user_id}")
                return True
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Ошибка при завершении инвентаризации {inventory_id}: {e}")
            raise DatabaseError(f"Ошибка при завершении инвентаризации: {e}")

