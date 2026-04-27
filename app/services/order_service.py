"""
Сервис для работы с заявками.

Содержит бизнес-логику для работы с заявками: создание, обновление,
получение данных, работа с услугами, запчастями, оплатами и комментариями.
"""
from typing import Optional, Dict, List, Any
from app.models.order import Order
from app.database.queries.order_queries import OrderQueries
from app.utils.cache import cache_result
from app.utils.validators import validate_order_data
from app.utils.pagination import Paginator
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.types import OrderDict, OrderTotalsDict, OrderFiltersDict
from app.utils.error_handlers import handle_service_error, log_error
from app.utils.performance_monitor import monitor_db_query
from app.utils.datetime_utils import get_moscow_now_str
import logging
import sqlite3

logger = logging.getLogger(__name__)


class OrderService:
    """Сервис для работы с заявками."""
    
    @staticmethod
    @cache_result(timeout=60, key_prefix='order')
    def get_order(order_id: int) -> Optional[Order]:
        """
        Получает заявку по ID с кэшированием.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Order или None
            
        Raises:
            ValidationError: Если order_id невалидный
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        return Order.get_by_id(order_id)
    
    @staticmethod
    # Временно отключен кэш для отладки
    # @cache_result(timeout=30, key_prefix='order_uuid')
    def get_order_by_uuid(order_uuid: str) -> Optional[Order]:
        """
        Получает заявку по UUID с кэшированием.
        
        Args:
            order_uuid: UUID заявки
            
        Returns:
            Order или None
            
        Raises:
            ValidationError: Если order_uuid невалидный
        """
        if not order_uuid or not order_uuid.strip():
            raise ValidationError("Неверный UUID заявки")
        
        logger.debug(f"Поиск заявки по UUID: {order_uuid.strip()}")
        
        try:
            result = Order.get_by_uuid(order_uuid.strip())
            if result:
                logger.debug(f"Заявка найдена: ID={result.id}, UUID={result.order_id}")
            else:
                logger.warning(f"Заявка с UUID {order_uuid.strip()} не найдена в БД")
            return result
        except Exception as e:
            logger.exception(f"Ошибка при получении заявки по UUID {order_uuid.strip()}: {e}")
            return None
    
    @staticmethod
    @monitor_db_query(threshold=1.0)
    def get_orders_with_details(filters: Optional[OrderFiltersDict] = None, 
                                page: int = 1, 
                                per_page: int = 50) -> Paginator:
        """
        Получает список заявок с деталями (оптимизированный запрос).
        
        Args:
            filters: Словарь с фильтрами для поиска заявок:
                - status: код статуса (str)
                - status_id: ID статуса (int)
                - customer_id: ID клиента (int)
                - device_id: ID устройства (int)
                - manager_id: ID менеджера (int)
                - master_id: ID мастера (int)
                - search: поисковый запрос (str)
                - date_from: дата начала (str, формат YYYY-MM-DD)
                - date_to: дата окончания (str, формат YYYY-MM-DD)
                - hidden: фильтр по скрытости (int, 0 или 1)
            page: Номер страницы (начинается с 1)
            per_page: Количество элементов на странице
            
        Returns:
            Paginator с заявками и метаданными пагинации
            
        Raises:
            ValidationError: Если параметры пагинации невалидны
        """
        if page < 1:
            raise ValidationError("Номер страницы должен быть >= 1")
        if per_page < 1:
            raise ValidationError("Количество элементов на странице должно быть >= 1")
        
        result = OrderQueries.get_orders_with_all_details(filters, page, per_page)
        return Paginator(
            items=result['items'],
            page=result['page'],
            per_page=result['per_page'],
            total=result['total']
        )
    
    @staticmethod
    def get_order_totals(order_id: int) -> OrderTotalsDict:
        """
        Получает все суммы по заявке (услуги, запчасти, оплаты, долг).
        
        Args:
            order_id: ID заявки
            
        Returns:
            Словарь с суммами:
            - services_total: общая стоимость услуг
            - parts_total: общая стоимость запчастей
            - payments_total: общая сумма оплат
            - debt: долг (services_total + parts_total - payments_total)
            
        Raises:
            ValidationError: Если order_id невалидный
            NotFoundError: Если заявка не найдена
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        return OrderQueries.get_order_totals(order_id)
    
    @staticmethod
    def get_order_full_data(order_id: int) -> Dict[str, Any]:
        """
        Получает полные данные заявки со всеми связанными данными.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Словарь с полными данными заявки, включая:
            - order: OrderDict - данные заявки
            - customer: CustomerDict - данные клиента
            - device: DeviceDict - данные устройства
            - services: List[Dict[str, Any]] - услуги заявки
            - parts: List[Dict[str, Any]] - запчасти заявки
            - payments: List[PaymentDict] - оплаты
            - comments: List[CommentDict] - комментарии
            - totals: OrderTotalsDict - суммы
            
        Raises:
            ValidationError: Если order_id невалидный
            NotFoundError: Если заявка не найдена
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        # Используем оптимизированный запрос
        flat_data = OrderQueries.get_order_full_details(order_id)
        
        if not flat_data:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        # Преобразуем плоский словарь в структурированный формат
        from app.services.payment_service import PaymentService
        from app.services.comment_service import CommentService
        
        # Разделяем данные на категории
        # Исключаем только финансовые поля из order, но оставляем связанные данные для обратной совместимости
        order = {k: v for k, v in flat_data.items() 
                if k not in ['services_total', 'parts_total', 'total', 'paid', 'debt']}
        
        # Добавляем алиасы для обратной совместимости с шаблоном
        # Шаблон ожидает order.client_name, order.phone, order.email напрямую
        if 'customer_name' in flat_data:
            order['client_name'] = flat_data.get('customer_name')
        if 'customer_phone' in flat_data:
            order['phone'] = flat_data.get('customer_phone')
        if 'customer_email' in flat_data:
            order['email'] = flat_data.get('customer_email')
        
        customer = {
            'id': flat_data.get('customer_id'),
            'name': flat_data.get('customer_name'),
            'phone': flat_data.get('customer_phone'),
            'email': flat_data.get('customer_email')
        }
        
        device = {
            'id': flat_data.get('device_id'),
            'serial_number': flat_data.get('serial_number'),
            'device_type_id': flat_data.get('device_type_id'),
            'device_type_name': flat_data.get('device_type_name'),
            'device_brand_id': flat_data.get('device_brand_id'),
            'device_brand_name': flat_data.get('device_brand_name')
        }
        
        # Получаем услуги, запчасти, оплаты и комментарии
        services = OrderQueries.get_order_services(order_id)
        parts = OrderQueries.get_order_parts(order_id)
        payments = PaymentService.get_order_payments(order_id)
        comments = CommentService.get_order_comments(order_id)
        
        # Получаем totals через get_order_totals для получения overpayment
        totals_data = OrderService.get_order_totals(order_id)
        
        totals = {
            'services_total': totals_data.get('services_total', 0),
            'parts_total': totals_data.get('parts_total', 0),
            'prepayment': totals_data.get('prepayment', 0),
            'total': totals_data.get('total', 0),
            'paid': totals_data.get('paid', 0),
            'debt': totals_data.get('debt', 0),
            'overpayment': totals_data.get('overpayment', 0)
        }
        
        return {
            'order': order,
            'customer': customer,
            'device': device,
            'services': services,
            'parts': parts,
            'payments': payments,
            'comments': comments,
            'totals': totals
        }
    
    @staticmethod
    def get_order_services(order_id: int) -> List[Dict]:
        """
        Получает услуги заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список услуг
        """
        return OrderQueries.get_order_services(order_id)
    
    @staticmethod
    def get_order_parts(order_id: int) -> List[Dict]:
        """
        Получает запчасти заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список запчастей
        """
        return OrderQueries.get_order_parts(order_id)
    
    @staticmethod
    def check_order_edit_allowed(order_id: int) -> bool:
        """
        Проверяет, разрешено ли редактирование заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            True если редактирование разрешено, False если заблокировано
            
        Raises:
            NotFoundError: Если заявка не найдена
        """
        from app.database.connection import get_db_connection
        import sqlite3
        
        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        # Проверяем флаги статуса
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT blocks_edit, is_final
                FROM order_statuses
                WHERE id = ?
            ''', (order.status_id,))
            status_row = cursor.fetchone()
            
            if status_row:
                blocks_edit = bool(status_row[0])
                is_final = bool(status_row[1])
                # Если хотя бы один флаг установлен, редактирование заблокировано
                if blocks_edit or is_final:
                    return False
        
        return True
    
    @staticmethod
    def get_order_payments(order_id: int) -> List[Dict]:
        """
        Получает оплаты заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список оплат
        """
        return OrderQueries.get_order_payments(order_id)
    
    @staticmethod
    def update_order_status(order_id: int, status_id: int, user_id: int = None, comment: str = None) -> Dict[str, Any]:
        """
        Обновляет статус заявки с триггерами (оплата, зарплата).
        
        Args:
            order_id: ID заявки
            status_id: ID нового статуса
            user_id: ID пользователя, выполняющего изменение
            comment: Комментарий к смене статуса
            
        Returns:
            Словарь с результатом:
            - success: True если успешно
            - triggers_payment_modal: True если нужно открыть окно оплаты
            - accrues_salary: True если начислена зарплата
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если заявка не найдена
            DatabaseError: Если произошла ошибка БД
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        if not status_id or status_id <= 0:
            raise ValidationError("Неверный ID статуса")
        
        # Проверяем, существует ли заявка
        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        try:
            from app.database.connection import get_db_connection
            import sqlite3
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Получаем старый статус перед обновлением
                cursor.execute('SELECT status_id FROM orders WHERE id = ?', (order_id,))
                old_status_row = cursor.fetchone()
                old_status_id = old_status_row[0] if old_status_row else None
                status_changed = old_status_id != status_id

                # Проверка баланса при переходе в закрывающий статус (accrues_salary или is_final)
                if status_changed:
                    cursor.execute('''
                        SELECT accrues_salary, COALESCE(is_final, 0), COALESCE(triggers_payment_modal, 0)
                        FROM order_statuses WHERE id = ?
                    ''', (status_id,))
                    new_status_row = cursor.fetchone()
                    if new_status_row:
                        accrues_salary_new = bool(new_status_row[0])
                        is_final_new = bool(new_status_row[1])
                        triggers_payment_new = bool(new_status_row[2])
                        if accrues_salary_new or is_final_new:
                            totals = OrderService.get_order_totals(order_id)
                            debt = float(totals.get('debt', 0) or 0)
                            overpayment = float(totals.get('overpayment', 0) or 0)
                            services_total = float(totals.get('services_total', 0) or 0)
                            parts_total = float(totals.get('parts_total', 0) or 0)
                            has_services_or_parts = services_total > 0 or parts_total > 0
                            # Долг: блокируем только если статус НЕ вызывает окно оплаты.
                            # Иначе разрешаем закрытие — откроется модалка внесения оплаты.
                            if debt > 0 and not triggers_payment_new:
                                raise ValidationError(
                                    'Нельзя закрыть заявку с отрицательным балансом. '
                                    'Добавьте недостающие товары и услуги или получите оплату от клиента.'
                                )
                            # Переплату запрещаем только если нет услуг/товаров (предоплата на пустую заявку)
                            if overpayment > 0 and not has_services_or_parts:
                                raise ValidationError(
                                    'Нельзя закрыть заявку с переплатой. '
                                    'Верните клиенту излишне полученные средства через процедуру возврата.'
                                )
                
                # Используем московское время для updated_at (как в created_at и order_status_history)
                from app.utils.datetime_utils import get_moscow_now_str
                updated_at_moscow = get_moscow_now_str()
                
                cursor.execute('''
                    UPDATE orders 
                    SET status_id = ?, updated_at = ?
                    WHERE id = ?
                ''', (status_id, updated_at_moscow, order_id))
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Заявка с ID {order_id} не найдена")
                
                # Логирование изменения статуса в order_status_history
                try:
                    from app.services.user_service import UserService
                    changed_by_username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            changed_by_username = user.get('username')
                    
                    logger.debug(f"Создание записи в order_status_history: order_id={order_id}, old_status_id={old_status_id}, new_status_id={status_id}, changed_by={user_id}, username={changed_by_username}")
                    # Используем московское время (UTC+3), как в action_logs
                    from app.utils.datetime_utils import get_moscow_now_str
                    current_time = get_moscow_now_str()
                    cursor.execute('''
                        INSERT INTO order_status_history 
                        (order_id, old_status_id, new_status_id, changed_by, changed_by_username, comment, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (order_id, old_status_id, status_id, user_id, changed_by_username, comment or 'Изменение статуса', current_time))
                    conn.commit()
                    logger.info(f"Запись в order_status_history успешно создана для заявки #{order_id}")
                except Exception as e:
                    logger.error(f"Не удалось залогировать изменение статуса в order_status_history для заявки #{order_id}: {e}", exc_info=True)
                    conn.commit()
                
                # Логирование в action_logs
                try:
                    from app.services.action_log_service import ActionLogService
                    from app.services.user_service import UserService
                    from app.services.reference_service import ReferenceService
                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            username = user.get('username')
                    
                    # Получаем названия статусов для читаемого отображения
                    statuses = ReferenceService.get_order_statuses()
                    old_status_name = None
                    new_status_name = None
                    
                    if old_status_id:
                        old_status = next((s for s in statuses if s['id'] == old_status_id), None)
                        if old_status:
                            old_status_name = old_status.get('name', f'ID: {old_status_id}')
                    
                    if status_id:
                        new_status = next((s for s in statuses if s['id'] == status_id), None)
                        if new_status:
                            new_status_name = new_status.get('name', f'ID: {status_id}')
                    
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='update',
                        entity_type='order',
                        entity_id=order_id,
                        details={
                            'field': 'status',
                            'status': {
                                'old_id': old_status_id,
                                'old_name': old_status_name,
                                'new_id': status_id,
                                'new_name': new_status_name
                            }
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать изменение статуса в action_logs: {e}")
                
                logger.info(f"Статус заявки {order_id} изменен на {status_id} пользователем {user_id}")
                
                # Сохраняем комментарий в раздел комментариев, если он был указан
                comment_added = False
                if comment and comment.strip() and comment.strip() != 'Изменение статуса':
                    try:
                        from app.services.user_service import UserService
                        author_name = 'Система'
                        if user_id:
                            author_name = UserService.get_user_display_name(user_id)
                        
                        # Добавляем комментарий через CommentService
                        from app.services.comment_service import CommentService
                        comment_text = f"Смена статуса: {comment.strip()}"
                        CommentService.add_comment(order_id, author_name, comment_text)
                        comment_added = True
                        logger.info(f"Комментарий при смене статуса сохранен для заявки #{order_id}")
                    except Exception as e:
                        logger.warning(f"Не удалось сохранить комментарий при смене статуса для заявки #{order_id}: {e}")
                
                # Получаем информацию о новом статусе для триггеров
                cursor.execute('''
                    SELECT triggers_payment_modal, accrues_salary, blocks_edit, 
                           is_final, requires_comment
                    FROM order_statuses
                    WHERE id = ?
                ''', (status_id,))
                status_row = cursor.fetchone()
                triggers_payment_modal = False
                accrues_salary = False
                blocks_edit = False
                is_final = False
                requires_comment = False
                
                if status_row:
                    triggers_payment_modal = bool(status_row[0])
                    accrues_salary = bool(status_row[1])
                    blocks_edit = bool(status_row[2]) if len(status_row) > 2 else False
                    is_final = bool(status_row[3]) if len(status_row) > 3 else False
                    requires_comment = bool(status_row[4]) if len(status_row) > 4 else False
                
                # Если статус финальный, также блокируем редактирование
                if is_final:
                    blocks_edit = True
                
                # Проверяем, изменился ли статус на самом деле
                status_changed = old_status_id != status_id
                
                # Проверяем долг перед открытием модалки оплаты
                # Модалка должна открываться только если:
                # 1. Статус действительно изменился (не повторная установка того же статуса)
                # 2. У статуса есть флаг triggers_payment_modal
                # 3. Есть долг (долг > 0)
                if triggers_payment_modal and status_changed:
                    try:
                        totals = OrderService.get_order_totals(order_id)
                        debt = totals.get('debt', 0.0)
                        services_total = float(totals.get('services_total', 0) or 0)
                        parts_total = float(totals.get('parts_total', 0) or 0)
                        total_revenue = services_total + parts_total
                        has_services_or_parts = total_revenue > 0
                        
                        # Открываем модалку при долге или при наличии услуг/товаров (внесение в кассу)
                        if debt <= 0 and not has_services_or_parts:
                            triggers_payment_modal = False
                            logger.info(f"Модалка оплаты не открывается: нет долга и нет услуг/товаров (заявка {order_id})")
                        elif debt > 0:
                            logger.info(f"Модалка оплаты будет открыта: долг = {debt:.2f} руб (заявка {order_id})")
                        else:
                            logger.info(f"Модалка оплаты будет открыта: есть услуги/товары на сумму {total_revenue:.2f} руб (заявка {order_id})")
                    except Exception as e:
                        logger.warning(f"Не удалось проверить долг заявки {order_id}: {e}")
                        # В случае ошибки не открываем модалку, чтобы избежать проблем
                        triggers_payment_modal = False
                elif triggers_payment_modal and not status_changed:
                    # Статус не изменился - повторная установка того же статуса
                    triggers_payment_modal = False
                    logger.info(f"Модалка оплаты не открывается: статус не изменился (заявка {order_id}, статус {status_id})")
                
                # Начисление зарплаты при смене статуса.
                # Важно: повторный перевод заявки в "зарплатный" статус не должен создавать
                # новые начисления и дублировать записи в отчете/action-logs.
                # Поэтому при смене статуса начисляем только если начислений по заявке еще нет.
                salary_accrued = False
                if accrues_salary and status_changed:
                    try:
                        from app.services.salary_service import SalaryService
                        existing_accruals = SalaryService.get_accruals_for_order(order_id) or []
                        if not existing_accruals:
                            accrual_ids = SalaryService.accrue_salary_for_order(order_id)
                        else:
                            # Если заявка изменилась после последнего начисления (новые услуги/товары/оплаты),
                            # пересчитываем начисления, иначе оставляем текущие.
                            if SalaryService.order_changed_since_last_accrual(order_id):
                                accrual_ids = SalaryService.accrue_salary_for_order(order_id, force_recalculate=True)
                                logger.info(
                                    f"Зарплата по заявке {order_id} пересчитана: "
                                    f"было {len(existing_accruals)} начислений, стало {len(accrual_ids)}"
                                )
                            else:
                                accrual_ids = [a.get('id') for a in existing_accruals if a.get('id')]
                                logger.info(
                                    f"Начисление зарплаты пропущено для заявки {order_id}: "
                                    f"изменений после начисления нет ({len(existing_accruals)} записей)"
                                )
                        salary_accrued = len(accrual_ids) > 0
                        logger.info(f"Зарплата по заявке {order_id}: {len(accrual_ids)} записей")
                    except Exception as e:
                        logger.error(f"Ошибка при начислении зарплаты по заявке {order_id}: {e}", exc_info=True)
                        # Не прерываем выполнение, просто логируем ошибку
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                
                return {
                    'success': True,
                    'triggers_payment_modal': triggers_payment_modal,
                    'accrues_salary': salary_accrued,
                    'blocks_edit': blocks_edit,
                    'is_final': is_final,
                    'requires_comment': requires_comment,
                    'comment_added': comment_added
                }
        except sqlite3.IntegrityError as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            logger.error(f"Ошибка БД при обновлении статуса заявки {order_id}: {e}")
            raise ValidationError(error_msg)
        except sqlite3.Error as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            logger.error(f"Ошибка БД при обновлении статуса заявки {order_id}: {e}")
            raise DatabaseError(error_msg)
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обновлении статуса заявки {order_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении статуса: {e}")
    
    @staticmethod
    def create_order(
        customer_name: str,
        phone: str,
        email: str,
        device_type_id: int,
        device_brand_id: int,
        manager_id: int,
        master_id: Optional[int] = None,
        serial_number: Optional[str] = None,
        prepayment: str = '0',
        prepayment_method: str = 'cash',
        password: Optional[str] = None,
        appearance: Optional[str] = None,
        comment: Optional[str] = None,
        symptom_tags: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Создает новую заявку.
        
        Args:
            customer_name: Имя клиента
            phone: Телефон клиента
            email: Email клиента
            device_type_id: ID типа устройства
            device_brand_id: ID бренда устройства
            manager_id: ID менеджера
            master_id: ID мастера (опционально)
            serial_number: Серийный номер (опционально)
            prepayment: Предоплата
            prepayment_method: Способ предоплаты (cash, card, transfer)
            password: Пароль от устройства
            appearance: Внешний вид
            comment: Комментарий
            symptom_tags: Теги симптомов
            model: Модель устройства
            user_id: ID пользователя, создающего заявку
            
        Returns:
            Словарь с данными созданной заявки (order_id, order_uuid)
            
        Raises:
            ValidationError: Если данные невалидны
            DatabaseError: Если произошла ошибка БД
        """
        from app.models.customer import Customer
        from app.models.device import Device
        from app.utils.validators import validate_phone, normalize_phone
        from app.utils.datetime_utils import get_moscow_now_str
        from app.database.connection import get_db_connection
        import sqlite3
        import uuid
        
        try:
            # Нормализация телефона
            phone = normalize_phone(phone)
            validate_phone(phone)
            
            # Стартовый статус при создании заявки:
            # 1) явно заданный в настройках (is_default), 2) code='new', 3) название "Новая", 4) первый в списке.
            from app.database.queries.reference_queries import ReferenceQueries
            statuses = ReferenceQueries.get_order_statuses()
            default_status = next((s for s in statuses if s.get('is_default') == 1), None)
            if not default_status:
                default_status = next((s for s in statuses if str(s.get('code') or '').strip().lower() == 'new'), None)
            if not default_status:
                default_status = next((s for s in statuses if str(s.get('name') or '').strip().lower() == 'новая'), None)
            if not default_status:
                default_status = statuses[0] if statuses else None
            
            order_uuid = str(uuid.uuid4())
            created_at = get_moscow_now_str()
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Клиент (создаем или обновляем)
                customer = Customer.get_by_phone(phone)
                customer_was_created = False
                if customer:
                    customer_id = customer.id
                    # Обновляем данные клиента
                    customer.update(name=customer_name, email=email)
                else:
                    customer = Customer.create(name=customer_name, phone=phone, email=email)
                    if not customer:
                        raise DatabaseError("Ошибка при создании клиента")
                    customer_id = customer.id
                    customer_was_created = True
                
                # 2. Устройство (создаем или находим существующее)
                devices = Device.get_by_customer_id(customer_id)
                device = None
                for d in devices:
                    if (d.device_type_id == device_type_id and 
                        d.device_brand_id == device_brand_id and 
                        d.serial_number == serial_number):
                        device = d
                        break
                
                device_was_created = False
                from app.services.device_service import DeviceService
                from app.database.queries.reference_queries import ReferenceQueries
                
                # Проверяем существование device_type_id и device_brand_id
                device_types = ReferenceQueries.get_device_types()
                device_brands = ReferenceQueries.get_device_brands()
                
                if not any(dt['id'] == device_type_id for dt in device_types):
                    logger.error(f"device_type_id {device_type_id} не существует в базе данных")
                    raise DatabaseError(f"Тип устройства с ID {device_type_id} не найден")
                
                if not any(db['id'] == device_brand_id for db in device_brands):
                    logger.error(f"device_brand_id {device_brand_id} не существует в базе данных")
                    raise DatabaseError(f"Бренд устройства с ID {device_brand_id} не найден")
                
                if not device:
                    # Используем DeviceService для создания устройства с полными данными
                    logger.debug(f"Создание устройства: customer_id={customer_id}, device_type_id={device_type_id}, device_brand_id={device_brand_id}")
                    device = DeviceService.create_device(
                        customer_id=customer_id,
                        device_type_id=device_type_id,
                        device_brand_id=device_brand_id,
                        serial_number=serial_number,
                        password=password,
                        symptom_tags=symptom_tags,
                        appearance_tags=appearance,
                        comment=None  # Комментарий к устройству не передается при создании заявки
                    )
                    if not device:
                        logger.error(f"DeviceService.create_device вернул None для device_type_id={device_type_id}, device_brand_id={device_brand_id}")
                        raise DatabaseError("Ошибка при создании устройства")
                    device_was_created = True
                else:
                    # Обновляем существующее устройство, если изменились поля
                    DeviceService.update_device(
                        device.id,
                        device_type_id=device_type_id,
                        device_brand_id=device_brand_id,
                        serial_number=serial_number,
                        password=password,
                        symptom_tags=symptom_tags,
                        appearance_tags=appearance
                    )
                
                device_id = device.id
                
                # 3. Заявка
                status_id = default_status['id'] if default_status else None
                status_code = default_status['code'] if default_status else 'new'
                
                # Нормализуем и обрабатываем model
                model_id_value = None
                model_text_value = None
                if model:
                    model_stripped = model.strip()
                    if model_stripped:
                        model_text_value = model_stripped
                        # Нормализуем название (первая буква заглавная)
                        normalized_model = model_stripped[0].upper() + model_stripped[1:] if len(model_stripped) > 1 else model_stripped.upper()
                        
                        # Ищем или создаем модель в order_models
                        cursor.execute('SELECT id FROM order_models WHERE name = ?', (normalized_model,))
                        model_row = cursor.fetchone()
                        if model_row:
                            model_id_value = model_row[0]
                        else:
                            # Создаем новую модель
                            cursor.execute('INSERT INTO order_models (name) VALUES (?)', (normalized_model,))
                            model_id_value = cursor.lastrowid
                            logger.debug(f"Создана новая модель: {normalized_model} (ID: {model_id_value})")
                
                logger.debug(f"Создание заявки: model={model_text_value}, model_id={model_id_value}")
                
                # Проверяем наличие колонок в таблице orders
                try:
                    cursor.execute("PRAGMA table_info(orders)")
                    columns = [row[1] for row in cursor.fetchall()]
                    has_model_column = 'model' in columns
                    has_model_id_column = 'model_id' in columns
                    has_prepayment_cents_column = 'prepayment_cents' in columns
                    logger.debug(f"Колонки в таблице orders: {columns}, has_model_column={has_model_column}, has_model_id_column={has_model_id_column}")
                except Exception as pragma_e:
                    logger.warning(f"Не удалось проверить структуру таблицы: {pragma_e}")
                    has_model_column = True
                    has_model_id_column = True
                    has_prepayment_cents_column = False
                
                try:
                    # Формируем список колонок и значений для INSERT
                    insert_columns = [
                        'order_id', 'device_id', 'customer_id', 'manager_id', 'master_id',
                        'status_id', 'status', 'prepayment', 'password', 'appearance', 
                        'comment', 'symptom_tags', 'hidden', 'created_at'
                    ]
                    insert_values = [
                        order_uuid, device_id, customer_id, manager_id, master_id,
                        status_id, status_code, prepayment, password, appearance,
                        comment, symptom_tags, 0, created_at
                    ]

                    # Вычисляем prepayment_value для использования в кассовой операции
                    try:
                        prepayment_value = float(prepayment or 0)
                    except Exception:
                        prepayment_value = 0.0
                    
                    # Добавляем prepayment_cents если колонка существует
                    if has_prepayment_cents_column:
                        insert_columns.append('prepayment_cents')
                        insert_values.append(int(round(prepayment_value * 100)))
                    
                    # Добавляем model и model_id если колонки существуют
                    if has_model_column:
                        insert_columns.append('model')
                        insert_values.append(model_text_value)
                    if has_model_id_column:
                        insert_columns.append('model_id')
                        insert_values.append(model_id_value)
                    
                    placeholders = ', '.join(['?'] * len(insert_values))
                    columns_str = ', '.join(insert_columns)
                    
                    cursor.execute(f'''
                        INSERT INTO orders ({columns_str})
                        VALUES ({placeholders})
                    ''', insert_values)
                except sqlite3.OperationalError as e:
                    logger.error(f"Ошибка SQL при создании заявки: {e}")
                    logger.error(f"Параметры: order_uuid={order_uuid}, device_id={device_id}, model={model_text_value}, model_id={model_id_value}")
                    raise DatabaseError(f"Ошибка при создании заявки: {e}")
                
                order_db_id = cursor.lastrowid
                
                # Сохраняем симптомы в order_symptoms (many-to-many)
                if symptom_tags:
                    import re
                    symptom_names = re.split(r'[,;\n\r]+', symptom_tags)
                    for symptom_name in symptom_names:
                        normalized = symptom_name.strip()
                        if not normalized:
                            continue
                        # Нормализуем (первая буква заглавная)
                        normalized = normalized[0].upper() + normalized[1:] if len(normalized) > 1 else normalized.upper()
                        
                        # Ищем или создаем симптом
                        cursor.execute('SELECT id FROM symptoms WHERE name = ?', (normalized,))
                        symptom_row = cursor.fetchone()
                        if symptom_row:
                            symptom_id = symptom_row[0]
                        else:
                            # Создаем новый симптом
                            cursor.execute('''
                                INSERT INTO symptoms (name, sort_order) 
                                VALUES (?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM symptoms))
                            ''', (normalized,))
                            symptom_id = cursor.lastrowid
                            logger.debug(f"Создан новый симптом: {normalized} (ID: {symptom_id})")
                        
                        # Создаем связь в order_symptoms
                        try:
                            cursor.execute('''
                                INSERT INTO order_symptoms (order_id, symptom_id) 
                                VALUES (?, ?)
                            ''', (order_db_id, symptom_id))
                        except sqlite3.IntegrityError:
                            # Связь уже существует (не должно быть, но на всякий случай)
                            pass
                
                # Сохраняем теги внешнего вида в order_appearance_tags (many-to-many)
                if appearance:
                    import re
                    tag_names = re.split(r'[,;\n\r]+', appearance)
                    for tag_name in tag_names:
                        normalized = tag_name.strip()
                        if not normalized:
                            continue
                        # Нормализуем (первая буква заглавная)
                        normalized = normalized[0].upper() + normalized[1:] if len(normalized) > 1 else normalized.upper()
                        
                        # Ищем или создаем тег
                        cursor.execute('SELECT id FROM appearance_tags WHERE name = ?', (normalized,))
                        tag_row = cursor.fetchone()
                        if tag_row:
                            tag_id = tag_row[0]
                        else:
                            # Создаем новый тег
                            cursor.execute('''
                                INSERT INTO appearance_tags (name, sort_order) 
                                VALUES (?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM appearance_tags))
                            ''', (normalized,))
                            tag_id = cursor.lastrowid
                            logger.debug(f"Создан новый тег внешнего вида: {normalized} (ID: {tag_id})")
                        
                        # Создаем связь в order_appearance_tags
                        try:
                            cursor.execute('''
                                INSERT INTO order_appearance_tags (order_id, appearance_tag_id) 
                                VALUES (?, ?)
                            ''', (order_db_id, tag_id))
                        except sqlite3.IntegrityError:
                            # Связь уже существует (не должно быть, но на всякий случай)
                            pass
                
                conn.commit()
                
                # Логирование изменения статуса
                if status_id and user_id:
                    try:
                        from app.database.connection import get_db_connection
                        from app.utils.datetime_utils import get_moscow_now_str
                        import sqlite3
                        with get_db_connection() as log_conn:
                            log_cursor = log_conn.cursor()
                            # Используем московское время (UTC+3), как в action_logs
                            current_time = get_moscow_now_str()
                            log_cursor.execute('''
                                INSERT INTO order_status_history 
                                (order_id, old_status_id, new_status_id, changed_by, changed_by_username, comment, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (order_db_id, None, status_id, user_id, None, 'Создание заявки', current_time))
                            log_conn.commit()
                    except Exception as e:
                        logger.warning(f"Не удалось залогировать создание заявки в order_status_history: {e}")
                
                # Логируем создание заявки в action_logs
                try:
                    from app.services.action_log_service import ActionLogService
                    from flask_login import current_user
                    from app.database.queries.reference_queries import ReferenceQueries
                    
                    log_user_id = user_id
                    log_username = None
                    if not log_user_id:
                        try:
                            log_user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                            log_username = current_user.username if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                        except (AttributeError, RuntimeError):
                            pass
                    
                    # Получаем названия для отображения
                    customer_name = customer.name if customer else customer_name
                    status_name = default_status.get('name', status_code) if default_status else status_code
                    
                    # Получаем названия типов устройств и брендов
                    device_types = ReferenceQueries.get_device_types()
                    device_brands = ReferenceQueries.get_device_brands()
                    device_type_name = next((dt['name'] for dt in device_types if dt['id'] == device_type_id), f'ID: {device_type_id}')
                    device_brand_name = next((db['name'] for db in device_brands if db['id'] == device_brand_id), f'ID: {device_brand_id}')
                    
                    # Получаем названия менеджера и мастера
                    managers = ReferenceQueries.get_managers()
                    masters = ReferenceQueries.get_masters()
                    manager_name = next((m['name'] for m in managers if m['id'] == manager_id), f'ID: {manager_id}') if manager_id else None
                    master_name = next((m['name'] for m in masters if m['id'] == master_id), f'ID: {master_id}') if master_id else None
                    
                    ActionLogService.log_action(
                        user_id=log_user_id,
                        username=log_username,
                        action_type='create',
                        entity_type='order',
                        entity_id=order_db_id,
                        details={
                            'UUID заявки': order_uuid,
                            'Клиент': customer_name,
                            'Устройство': f"{device_type_name} {device_brand_name}",
                            'Серийный номер': serial_number,
                            'Статус': status_name,
                            'Менеджер': manager_name,
                            'Мастер': master_name
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать создание заявки в action_logs: {e}")
                
                # Логируем создание клиента, если он был создан
                if customer_was_created:
                    try:
                        from app.services.action_log_service import ActionLogService
                        from flask_login import current_user
                        log_user_id = user_id
                        log_username = None
                        if not log_user_id:
                            try:
                                log_user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                                log_username = current_user.username if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                            except Exception as e:
                                logger.debug("get current_user for action log: %s", e)
                        
                        ActionLogService.log_action(
                            user_id=log_user_id,
                            username=log_username,
                            action_type='create',
                            entity_type='customer',
                            entity_id=customer_id,
                            details={
                                'name': customer_name,
                                'phone': phone,
                                'email': email or 'Не указан'
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось залогировать создание клиента при создании заявки: {e}")
                
                # Устройство не логируется отдельно при создании заявки - 
                # информация об устройстве уже включена в details заявки
                
                # Создаем кассовую операцию для предоплаты, если она указана
                if prepayment_value and prepayment_value > 0:
                    try:
                        # Важно: предоплата должна быть такой же "оплатой", как обычная оплата:
                        # - запись в payments(kind='deposit') (чтобы считалась в totals и отображалась в заявке)
                        # - кассовая операция будет создана автоматически (и будет payment_id, т.е. будет "чек")
                        from app.services.payment_service import PaymentService
                            
                        # Получаем username для автора
                        username = None
                        if user_id:
                            try:
                                cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                                user_row = cursor.fetchone()
                                if user_row:
                                    username = user_row[0]
                            except Exception:
                                username = None

                        # Валидация способа предоплаты
                        valid_methods = ('cash', 'card', 'transfer')
                        if prepayment_method not in valid_methods:
                            prepayment_method = 'cash'

                        # Защита от дублей при повторном запросе создания заявки
                        idem_key = f"order_create_prepayment:{order_uuid}"

                        PaymentService.add_payment(
                            order_id=order_db_id,
                            amount=prepayment_value,
                            payment_type=prepayment_method,
                            user_id=user_id,
                            username=username,
                            comment="Предоплата при создании заявки",
                            kind="deposit",
                            status="captured",
                            idempotency_key=idem_key,
                        )
                        logger.info(f"Создана предоплата (payment) {prepayment_value} руб. по заявке {order_db_id}")
                    except Exception as e:
                        # Логируем ошибку, но не прерываем создание заявки
                        logger.error(f"Ошибка при создании предоплаты для заявки: {e}")
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                clear_cache(key_prefix='customer')
                clear_cache(key_prefix='finance')
                
                return {
                    'id': order_db_id,
                    'order_id': order_uuid,
                    'customer_id': customer_id,
                    'device_id': device_id
                }
        except ValidationError:
            raise
        except sqlite3.IntegrityError as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            log_error(e, context=f"Создание заявки для клиента {customer_name}", 
                     user_id=user_id)
            raise ValidationError(error_msg)
        except sqlite3.Error as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            log_error(e, context=f"Создание заявки для клиента {customer_name}", 
                     user_id=user_id)
            raise DatabaseError(error_msg)
            raise DatabaseError("Ошибка базы данных при создании заявки")
        except Exception as e:
            log_error(e, context=f"Создание заявки для клиента {customer_name}", 
                     user_id=user_id)
            raise DatabaseError("Произошла ошибка при создании заявки")
    
    @staticmethod
    def add_order_service(
        order_id: int,
        service_id: Optional[int] = None,
        quantity: int = 1,
        price: Optional[float] = None,
        name: Optional[str] = None,
        base_price: Optional[float] = None,
        cost_price: Optional[float] = None,
        discount_type: Optional[str] = None,
        discount_value: Optional[float] = None,
        warranty_days: Optional[int] = None,
        executor_id: Optional[int] = None,
    ) -> int:
        """
        Добавляет услугу к заявке.
        
        Args:
            order_id: ID заявки
            service_id: ID услуги (опционально для разовых услуг)
            quantity: Количество
            price: Цена (обязательна для разовых услуг)
            name: Название услуги (обязательно для разовых услуг)
            
        Returns:
            ID созданной записи order_service
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если заявка или услуга не найдены
            DatabaseError: Если произошла ошибка БД
        """
        from app.database.connection import get_db_connection
        from app.database.queries.reference_queries import ReferenceQueries
        import sqlite3
        
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        # Проверяем существование заявки
        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        # Валидация: либо service_id, либо name должны быть указаны
        if not service_id and not name:
            raise ValidationError("Необходимо указать либо ID услуги, либо название разовой услуги")
        
        if service_id and service_id <= 0:
            raise ValidationError("Неверный ID услуги")
        
        if name:
            name = name.strip()
            if not name:
                raise ValidationError("Название разовой услуги не может быть пустым")
        
        try:
            # Если указан service_id, получаем цену из справочника, если не указана
            if service_id:
                if price is None:
                    services = ReferenceQueries.get_services()
                    service = next((s for s in services if s['id'] == service_id), None)
                    if not service:
                        raise NotFoundError(f"Услуга с ID {service_id} не найдена")
                    price = float(service['price'])
            else:
                # Для разовой услуги цена обязательна
                if price is None or price <= 0:
                    raise ValidationError("Для разовой услуги необходимо указать цену")

            # base_price: используется как "прайсовая" цена перед скидкой
            if base_price is None:
                base_price = float(price or 0)

            # Применяем скидку/наценку (для расчета итоговой цены строки)
            if discount_type and discount_value is not None:
                dt = str(discount_type).lower()
                try:
                    dv = float(discount_value)
                except Exception:
                    dv = None
                if dv is not None:
                    if dt in ('percent', '%'):
                        price = float(base_price) * (1 - dv / 100.0)
                    elif dt in ('amount', 'rub', '₽'):
                        price = float(base_price) - dv
                    if price is not None and price < 0:
                        price = 0.0

            # Гарантия по умолчанию из общих настроек
            if warranty_days is None:
                try:
                    from app.services.settings_service import SettingsService
                    warranty_days = int((SettingsService.get_general_settings() or {}).get('default_warranty_days') or 30)
                except Exception:
                    warranty_days = 30
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO order_services (
                        order_id, service_id, name, quantity,
                        price, base_price, cost_price,
                        discount_type, discount_value,
                        warranty_days, executor_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_id, service_id, name, quantity,
                    price, base_price, cost_price,
                    discount_type, discount_value,
                    warranty_days, executor_id
                ))
                conn.commit()
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                
                return cursor.lastrowid
        except (ValidationError, NotFoundError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при добавлении услуги к заявке {order_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при добавлении услуги: {e}")
            raise DatabaseError(f"Ошибка при добавлении услуги: {e}")
    
    @staticmethod
    def delete_order_service(order_service_id: int) -> bool:
        """
        Удаляет услугу из заявки.
        
        Args:
            order_service_id: ID записи order_service
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если запись не найдена
            DatabaseError: Если произошла ошибка БД
        """
        from app.database.connection import get_db_connection
        import sqlite3
        
        if not order_service_id or order_service_id <= 0:
            raise ValidationError("Неверный ID услуги заявки")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM order_services WHERE id = ?', (order_service_id,))
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Услуга заявки с ID {order_service_id} не найдена")
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                
                return True
        except (ValidationError, NotFoundError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при удалении услуги {order_service_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при удалении услуги: {e}")
            raise DatabaseError(f"Ошибка при удалении услуги: {e}")
    
    @staticmethod
    def add_order_part(
        order_id: int,
        part_id: Optional[int] = None,
        quantity: int = 1,
        price: Optional[float] = None,
        name: Optional[str] = None,
        base_price: Optional[float] = None,
        purchase_price: Optional[float] = None,
        discount_type: Optional[str] = None,
        discount_value: Optional[float] = None,
        warranty_days: Optional[int] = None,
        executor_id: Optional[int] = None,
    ) -> int:
        """
        Добавляет запчасть к заявке и списывает со склада.
        
        Args:
            order_id: ID заявки
            part_id: ID запчасти (опционально для разовых товаров)
            quantity: Количество
            price: Цена (обязательна для разовых товаров)
            name: Название товара (обязательно для разовых товаров)
            
        Returns:
            ID созданной записи order_part
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если заявка или запчасть не найдены
            DatabaseError: Если произошла ошибка БД или недостаточно товара на складе
        """
        from app.database.connection import get_db_connection
        import sqlite3
        
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        # Валидация: либо part_id, либо name должны быть указаны
        if not part_id and not name:
            raise ValidationError("Необходимо указать либо ID товара, либо название разового товара")
        
        if part_id and part_id <= 0:
            raise ValidationError("Неверный ID запчасти")
        
        if name:
            name = name.strip()
            if not name:
                raise ValidationError("Название разового товара не может быть пустым")
        
        if quantity <= 0:
            raise ValidationError("Количество должно быть больше нуля")
        
        # Проверяем существование заявки
        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        try:
            purchase_price_snapshot = None
            order_part_id = None  # Инициализируем переменную
            
            if part_id:
                # Для товара из справочника - проверяем склад и получаем цены
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Получаем информацию о товаре со склада (цены/остатки/себестоимость)
                    from app.database.queries.warehouse_queries import WarehouseQueries
                    part = WarehouseQueries.get_part_by_id(part_id)
                    if not part:
                        raise NotFoundError(f"Запчасть с ID {part_id} не найдена")
                    
                    stock_quantity = part.get('stock_quantity', 0)
                    
                    # Проверяем наличие на складе
                    if stock_quantity < quantity:
                        raise DatabaseError(
                            f"Недостаточно запчасти на складе: требуется {quantity}, есть {stock_quantity}"
                        )
                    
                    # Получаем цену, если не указана
                    if price is None:
                        # В текущей схеме розничная цена хранится в parts.price (WarehouseQueries также отдает retail_price)
                        price = float(part.get('price', part.get('retail_price', 0)) or 0)

                    if base_price is None:
                        base_price = float(price or 0)

                    # Снимок себестоимости на момент продажи (для отчетов/маржи)
                    purchase_price_snapshot = purchase_price if purchase_price is not None else part.get('purchase_price')
                    try:
                        purchase_price_snapshot = float(purchase_price_snapshot) if purchase_price_snapshot is not None else None
                    except Exception:
                        purchase_price_snapshot = None
                    
                    # Гарантия: сначала из товара на складе, затем из общих настроек
                    if warranty_days is None:
                        try:
                            warranty_days = int(part.get('warranty_days')) if part.get('warranty_days') is not None else None
                        except Exception:
                            warranty_days = None
                    if warranty_days is None:
                        try:
                            from app.services.settings_service import SettingsService
                            warranty_days = int((SettingsService.get_general_settings() or {}).get('default_warranty_days') or 30)
                        except Exception:
                            warranty_days = 30

                    # Скидка/наценка
                    if discount_type and discount_value is not None:
                        dt = str(discount_type).lower()
                        try:
                            dv = float(discount_value)
                        except Exception:
                            dv = None
                        if dv is not None:
                            if dt in ('percent', '%'):
                                price = float(base_price) * (1 - dv / 100.0)
                            elif dt in ('amount', 'rub', '₽'):
                                price = float(base_price) - dv
                            if price is not None and price < 0:
                                price = 0.0
                    
                    # Не агрегируем одинаковые товары в одну строку: у строки могут быть разные
                    # исполнитель/скидка/гарантия/себестоимость (важно для будущего расчета зарплаты).
                    cursor.execute('''
                        INSERT INTO order_parts (
                            order_id, part_id, name, quantity,
                            price, purchase_price,
                            base_price, discount_type, discount_value,
                            warranty_days, executor_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        order_id, part_id, None, quantity,
                        price, purchase_price_snapshot,
                        base_price, discount_type, discount_value,
                        warranty_days, executor_id
                    ))
                    order_part_id = cursor.lastrowid
                    conn.commit()
                    
                    # Списываем со склада через WarehouseService
                    from app.services.warehouse_service import WarehouseService
                    from flask_login import current_user
                    user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
                    
                    WarehouseService.record_sale(
                        part_id=part_id,
                        quantity=quantity,
                        order_id=order_id,
                        user_id=user_id
                    )

                    # Очищаем кэш и возвращаем ID созданной позиции
                    from app.utils.cache import clear_cache
                    clear_cache(key_prefix='order')
                    return order_part_id
            else:
                # Для разового товара цена обязательна
                if price is None or price <= 0:
                    raise ValidationError("Для разового товара необходимо указать цену")

                if base_price is None:
                    base_price = float(price or 0)

                if warranty_days is None:
                    try:
                        from app.services.settings_service import SettingsService
                        warranty_days = int((SettingsService.get_general_settings() or {}).get('default_warranty_days') or 30)
                    except Exception:
                        warranty_days = 30

                if discount_type and discount_value is not None:
                    dt = str(discount_type).lower()
                    try:
                        dv = float(discount_value)
                    except Exception:
                        dv = None
                    if dv is not None:
                        if dt in ('percent', '%'):
                            price = float(base_price) * (1 - dv / 100.0)
                        elif dt in ('amount', 'rub', '₽'):
                            price = float(base_price) - dv
                        if price is not None and price < 0:
                            price = 0.0
                
                # Для разовых товаров не списываем со склада
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO order_parts (
                            order_id, part_id, name, quantity,
                            price, purchase_price,
                            base_price, discount_type, discount_value,
                            warranty_days, executor_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        order_id, None, name, quantity,
                        price, purchase_price,
                        base_price, discount_type, discount_value,
                        warranty_days, executor_id
                    ))
                    conn.commit()
                    order_part_id = cursor.lastrowid
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                
                return order_part_id
        except (ValidationError, NotFoundError, DatabaseError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при добавлении запчасти к заявке {order_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при добавлении запчасти: {e}")
            raise DatabaseError(f"Ошибка при добавлении запчасти: {e}")

    @staticmethod
    def update_order_service_item(order_service_id: int, updates: Dict[str, Any], user_id: Optional[int] = None) -> int:
        """
        Обновляет позицию услуги в заявке.

        Args:
            order_service_id: ID строки order_services
            updates: словарь обновляемых полей (quantity, price, cost_price, discount_type, discount_value, warranty_days, executor_id)
            user_id: ID пользователя (для логов/будущего)

        Returns:
            order_id
        """
        from app.database.connection import get_db_connection
        import sqlite3

        if not order_service_id or order_service_id <= 0:
            raise ValidationError("Неверный ID позиции услуги")

        updates = updates or {}
        allowed = {
            'quantity': 'quantity',
            'price': 'price',
            'cost_price': 'cost_price',
            'discount_type': 'discount_type',
            'discount_value': 'discount_value',
            'warranty_days': 'warranty_days',
            'executor_id': 'executor_id'
        }

        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, order_id FROM order_services WHERE id = ?', (order_service_id,))
                row = cursor.fetchone()
                if not row:
                    raise NotFoundError(f"Позиция услуги с ID {order_service_id} не найдена")
                order_id = int(row['order_id'])

                set_sql = []
                params = []
                for key, col in allowed.items():
                    if key in updates:
                        set_sql.append(f"{col} = ?")
                        params.append(updates.get(key))

                if not set_sql:
                    return order_id

                cursor.execute(
                    f"UPDATE order_services SET {', '.join(set_sql)} WHERE id = ?",
                    (*params, order_service_id)
                )
                # Обновляем updated_at заявки — нужно для order_changed_since_last_accrual (пересчёт зарплаты при reload)
                cursor.execute(
                    "UPDATE orders SET updated_at = ? WHERE id = ?",
                    (get_moscow_now_str(), order_id)
                )
                conn.commit()

            from app.utils.cache import clear_cache
            clear_cache(key_prefix='order')
            return order_id
        except (ValidationError, NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Ошибка при обновлении позиции услуги {order_service_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при обновлении позиции услуги: {e}")

    @staticmethod
    def update_order_part_item(order_part_id: int, updates: Dict[str, Any], user_id: Optional[int] = None) -> int:
        """
        Обновляет позицию товара в заявке. Если позиция привязана к складу (part_id),
        то при изменении количества корректирует склад через WarehouseService (sale/return).

        Args:
            order_part_id: ID строки order_parts
            updates: словарь обновляемых полей (quantity, price, purchase_price, discount_type, discount_value, warranty_days, executor_id)
            user_id: ID пользователя

        Returns:
            order_id
        """
        from app.database.connection import get_db_connection
        import sqlite3

        if not order_part_id or order_part_id <= 0:
            raise ValidationError("Неверный ID позиции товара")

        updates = updates or {}
        allowed = {
            'quantity': 'quantity',
            'price': 'price',
            'purchase_price': 'purchase_price',
            'discount_type': 'discount_type',
            'discount_value': 'discount_value',
            'warranty_days': 'warranty_days',
            'executor_id': 'executor_id'
        }

        # Сначала получаем текущие данные, чтобы понимать изменение количества и ссылку на склад
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, order_id, part_id, quantity FROM order_parts WHERE id = ?', (order_part_id,))
                row = cursor.fetchone()
                if not row:
                    raise NotFoundError(f"Позиция товара с ID {order_part_id} не найдена")
                order_id = int(row['order_id'])
                part_id = row['part_id']
                old_qty = int(row['quantity'] or 0)

            new_qty = old_qty
            if 'quantity' in updates and updates.get('quantity') is not None:
                new_qty = int(updates.get('quantity') or 0)
            if new_qty <= 0:
                raise ValidationError("Количество должно быть больше 0")

            diff = new_qty - old_qty

            # ИСПРАВЛЕНИЕ БАГА: Объединяем склад и order_parts в одну транзакцию для атомарности
            
            # Используем ОДНУ транзакцию для склада и order_parts
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Корректировка склада в той же транзакции, если позиция привязана к складу
                if part_id and diff != 0:
                    if diff > 0:
                        # Продажа: уменьшаем остаток
                        cursor.execute('SELECT id, stock_quantity FROM parts WHERE id = ? AND is_deleted = 0', (part_id,))
                        part = cursor.fetchone()
                        if not part:
                            raise NotFoundError(f"Товар с ID {part_id} не найден")
                        
                        current_stock = part[1]
                        if current_stock < diff:
                            raise ValidationError(
                                f"Недостаточно товара на складе. Текущий остаток: {current_stock}, требуется: {diff}"
                            )
                        
                        new_stock = current_stock - diff
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
                        ''', (part_id, -diff, order_id, user_id, f"Продажа в заявке #{order_id}"))
                    else:
                        # Возврат: увеличиваем остаток
                        cursor.execute('SELECT id FROM parts WHERE id = ? AND is_deleted = 0', (part_id,))
                        if not cursor.fetchone():
                            raise NotFoundError(f"Товар с ID {part_id} не найден")
                        
                        cursor.execute('''
                            UPDATE parts 
                            SET stock_quantity = stock_quantity + ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (abs(diff), part_id))
                        
                        # Создаем движение
                        cursor.execute('''
                            INSERT INTO stock_movements 
                            (part_id, movement_type, quantity, reference_id, reference_type, created_by, notes)
                            VALUES (?, 'return', ?, ?, 'order', ?, ?)
                        ''', (part_id, abs(diff), order_id, user_id, f"Возврат в заявке #{order_id}"))
                
                # Обновляем order_parts в той же транзакции
                set_sql = []
                params = []
                for key, col in allowed.items():
                    if key in updates:
                        set_sql.append(f"{col} = ?")
                        params.append(updates.get(key))

                if set_sql:
                    cursor.execute(
                        f"UPDATE order_parts SET {', '.join(set_sql)} WHERE id = ?",
                        (*params, order_part_id)
                    )
                    # Обновляем updated_at заявки — нужно для order_changed_since_last_accrual (пересчёт зарплаты при reload)
                    cursor.execute(
                        "UPDATE orders SET updated_at = ? WHERE id = ?",
                        (get_moscow_now_str(), order_id)
                    )
                
                # Коммитим ВМЕСТЕ: склад + order_parts (атомарно)
                conn.commit()

            from app.utils.cache import clear_cache
            clear_cache(key_prefix='order')
            return order_id
        except (ValidationError, NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Ошибка при обновлении позиции товара {order_part_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при обновлении позиции товара: {e}")
    
    @staticmethod
    @handle_service_error
    def sell_items(
        order_id: int,
        services: List[Dict[str, Any]] = None,
        parts: List[Dict[str, Any]] = None,
        payment: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Объединенная продажа услуг и товаров с автоматическим списанием.
        
        Args:
            order_id: ID заявки
            services: Список услуг [{'service_id': int, 'quantity': int, 'price': float}]
            parts: Список запчастей [{'part_id': int, 'quantity': int, 'price': float}]
            payment: Данные оплаты {'amount': float, 'payment_type': str, 'comment': str}
            user_id: ID пользователя
            
        Returns:
            Словарь с результатами: services_added, parts_added, payment_id
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если заявка не найдена
            DatabaseError: Если недостаточно товара на складе
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        # Проверяем существование заявки
        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        services = services or []
        parts = parts or []
        
        if not services and not parts:
            raise ValidationError("Должна быть хотя бы одна услуга или запчасть")
        
        results = {
            'services_added': [],
            'parts_added': [],
            'payment_id': None
        }
        
        try:
            # Добавляем услуги
            for service in services:
                service_id = service.get('service_id')
                quantity = service.get('quantity', 1)
                price = service.get('price')
                
                if not service_id:
                    continue
                
                service_order_id = OrderService.add_order_service(
                    order_id=order_id,
                    service_id=service_id,
                    quantity=quantity,
                    price=price
                )
                results['services_added'].append(service_order_id)
            
            # Добавляем запчасти (автоматически списываются со склада)
            for part in parts:
                part_id = part.get('part_id')
                quantity = part.get('quantity', 1)
                price = part.get('price')
                
                if not part_id:
                    continue
                
                part_order_id = OrderService.add_order_part(
                    order_id=order_id,
                    part_id=part_id,
                    quantity=quantity,
                    price=price
                )
                results['parts_added'].append(part_order_id)
            
            # Добавляем оплату, если указана
            if payment:
                from app.services.payment_service import PaymentService
                
                # Получаем username из user_id, если не передан
                username = payment.get('username')
                if not username and user_id:
                    try:
                        from app.database.connection import get_db_connection
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                            user_row = cursor.fetchone()
                            if user_row:
                                username = user_row[0]
                    except Exception as e:
                        logger.warning(f"Не удалось получить username для user_id {user_id}: {e}")
                
                payment_id = PaymentService.add_payment(
                    order_id=order_id,
                    amount=payment.get('amount', 0),
                    payment_type=payment.get('payment_type', 'cash'),
                    user_id=user_id,
                    username=username,
                    comment=payment.get('comment')
                )
                results['payment_id'] = payment_id
            
            return results
        except (ValidationError, NotFoundError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Ошибка при объединенной продаже для заявки {order_id}: {e}")
            raise DatabaseError(f"Ошибка при продаже: {e}")
    
    @staticmethod
    def delete_order_part(order_part_id: int) -> bool:
        """
        Удаляет запчасть из заявки и возвращает на склад.
        
        Args:
            order_part_id: ID записи order_part
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если запись не найдена
            DatabaseError: Если произошла ошибка БД
        """
        from app.database.connection import get_db_connection
        import sqlite3
        
        if not order_part_id or order_part_id <= 0:
            raise ValidationError("Неверный ID запчасти заявки")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем информацию о запчасти перед удалением
                cursor.execute('''
                    SELECT part_id, quantity FROM order_parts WHERE id = ?
                ''', (order_part_id,))
                row = cursor.fetchone()
                
                if not row:
                    raise NotFoundError(f"Запчасть заявки с ID {order_part_id} не найдена")
                
                part_id, quantity = row
                
                # Получаем order_id для возврата
                cursor.execute('SELECT order_id FROM order_parts WHERE id = ?', (order_part_id,))
                order_row = cursor.fetchone()
                order_id = order_row[0] if order_row else None
                
                # Удаляем запчасть из заявки
                cursor.execute('DELETE FROM order_parts WHERE id = ?', (order_part_id,))
                conn.commit()
                
                # Возвращаем на склад через WarehouseService
                if order_id:
                    from app.services.warehouse_service import WarehouseService
                    from flask_login import current_user
                    user_id = current_user.id if hasattr(current_user, 'id') and current_user.is_authenticated else None
                    
                    WarehouseService.record_return(
                        part_id=part_id,
                        quantity=quantity,
                        order_id=order_id,
                        user_id=user_id
                    )
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                
                return True
        except (ValidationError, NotFoundError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при удалении запчасти {order_part_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при удалении запчасти: {e}")
            raise DatabaseError(f"Ошибка при удалении запчасти: {e}")
    
    @staticmethod
    def toggle_visibility(order_id: int, hidden: bool, user_id: Optional[int] = None, reason: Optional[str] = None) -> bool:
        """
        Скрывает или показывает заявку.
        
        Args:
            order_id: ID заявки
            hidden: True для скрытия, False для показа
            user_id: ID пользователя
            reason: Причина изменения
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если заявка не найдена
            DatabaseError: Если произошла ошибка БД
        """
        from app.database.connection import get_db_connection
        from app.database.queries.comment_queries import CommentQueries
        import sqlite3
        
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        # Проверяем существование заявки
        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                hidden_value = 1 if hidden else 0
                cursor.execute('SELECT COALESCE(is_deleted, 0) FROM orders WHERE id = ?', (order_id,))
                deleted_row = cursor.fetchone()
                if deleted_row and int(deleted_row[0] or 0) == 1:
                    raise ValidationError("Удаленная заявка не может быть показана или скрыта")

                now_moscow = get_moscow_now_str()
                cursor.execute('''
                    UPDATE orders 
                    SET hidden = ?, updated_at = ?
                    WHERE id = ?
                ''', (hidden_value, now_moscow, order_id))
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Заявка с ID {order_id} не найдена")
                
                # Логируем изменение видимости
                try:
                    from app.services.user_service import UserService
                    changed_by = 'Система'
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        if user:
                            changed_by = user.username
                    
                    # Логируем в order_visibility_history
                    cursor.execute('''
                        INSERT INTO order_visibility_history (order_id, hidden, changed_by, reason, changed_at)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (order_id, hidden_value, changed_by, reason, now_moscow))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Не удалось залогировать изменение видимости: {e}")
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                
                return True
        except (ValidationError, NotFoundError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при изменении видимости заявки {order_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при изменении видимости: {e}")
            raise DatabaseError(f"Ошибка при изменении видимости: {e}")

    @staticmethod
    def soft_delete_order(order_id: int, reason: str, user_id: Optional[int] = None) -> bool:
        """
        Выполняет мягкое удаление заявки.

        Заявка остается в БД, но исключается из рабочих списков.
        """
        from app.database.connection import get_db_connection
        import sqlite3

        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        if not reason or not reason.strip():
            raise ValidationError("Причина удаления обязательна")

        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Блокируем удаление, если есть активные оплаты.
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM payments
                    WHERE order_id = ?
                      AND (is_cancelled = 0 OR is_cancelled IS NULL)
                ''', (order_id,))
                active_payments = int((cursor.fetchone() or [0])[0] or 0)
                if active_payments > 0:
                    raise ValidationError(
                        "Нельзя удалить заявку с активными оплатами. Сначала отмените оплаты, затем удалите заявку."
                    )

                now_moscow = get_moscow_now_str()
                cursor.execute('''
                    UPDATE orders
                    SET is_deleted = 1,
                        hidden = 0,
                        deleted_at = ?,
                        deleted_by_id = ?,
                        deleted_reason = ?,
                        updated_at = ?
                    WHERE id = ?
                      AND (is_deleted = 0 OR is_deleted IS NULL)
                ''', (now_moscow, user_id, reason.strip(), now_moscow, order_id))
                if cursor.rowcount == 0:
                    raise ValidationError("Заявка уже удалена")

                conn.commit()

                try:
                    from app.services.action_log_service import ActionLogService
                    from app.services.user_service import UserService

                    username = None
                    if user_id:
                        user = UserService.get_user_by_id(user_id)
                        username = user.username if user else None

                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='delete',
                        entity_type='order',
                        entity_id=order_id,
                        description=f"Заявка #{order.order_id or order.id} мягко удалена",
                        details={
                            'reason': reason.strip(),
                            'order_uuid': order.order_id,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать soft-delete заявки {order_id}: {e}")

                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                clear_cache(key_prefix='finance')

                return True
        except (ValidationError, NotFoundError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при мягком удалении заявки {order_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при мягком удалении заявки {order_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении заявки: {e}")

