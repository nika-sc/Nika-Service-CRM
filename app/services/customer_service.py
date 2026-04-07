"""
Сервис для работы с клиентами.
"""
from typing import Optional, Dict, List
from app.models.customer import Customer
from app.database.queries.customer_queries import CustomerQueries
from app.utils.cache import cache_result, clear_cache
from app.utils.validators import validate_customer_data
from app.utils.pagination import Paginator
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.services.action_log_service import ActionLogService
import logging

logger = logging.getLogger(__name__)


class CustomerService:
    """Сервис для работы с клиентами."""
    
    @staticmethod
    @cache_result(timeout=300, key_prefix='customer')
    def get_customer(customer_id: int) -> Optional[Customer]:
        """
        Получает клиента по ID с кэшированием.
        
        Args:
            customer_id: ID клиента
            
        Returns:
            Customer или None
        """
        return Customer.get_by_id(customer_id)
    
    @staticmethod
    @cache_result(timeout=300, key_prefix='customer_phone')
    def get_customer_by_phone(phone: str) -> Optional[Customer]:
        """
        Получает клиента по телефону с кэшированием.
        
        Args:
            phone: Номер телефона
            
        Returns:
            Customer или None
        """
        return Customer.get_by_phone(phone)
    
    @staticmethod
    def get_customer_orders(customer_id: int, limit: int = 50) -> List[Dict]:
        """
        Получает заявки клиента.
        
        Args:
            customer_id: ID клиента
            limit: Максимальное количество заявок
            
        Returns:
            Список заявок
        """
        try:
            from app.database.connection import get_db_connection
            import sqlite3
            
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        o.id,
                        o.order_id,
                        o.created_at,
                        o.model,
                        o.symptom_tags,
                        o.appearance,
                        d.device_type_id,
                        d.device_brand_id,
                        d.serial_number,
                        COALESCE(os.code, o.status) AS status,
                        o.prepayment,
                        dt.name AS device_type,
                        db.name AS device_brand,
                        os.name AS status_name,
                        os.color AS status_color,
                        (SELECT COALESCE(SUM(p.amount), 0)
                         FROM payments p WHERE p.order_id = o.id
                         AND (p.is_cancelled = 0 OR p.is_cancelled IS NULL)) AS total_paid
                    FROM orders o
                    LEFT JOIN devices d ON d.id = o.device_id
                    LEFT JOIN device_types dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands db ON db.id = d.device_brand_id
                    LEFT JOIN order_statuses os ON os.id = o.status_id
                    WHERE o.customer_id = ? AND (o.hidden = 0 OR o.hidden IS NULL)
                    ORDER BY o.created_at DESC
                    LIMIT ?
                ''', (customer_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении заявок клиента {customer_id}: {e}")
            return []
    
    @staticmethod
    def get_customer_shop_sales(customer_id: int, limit: int = 50) -> List[Dict]:
        """
        Получает продажи из магазина для клиента.
        
        Args:
            customer_id: ID клиента
            limit: Максимальное количество продаж
            
        Returns:
            Список продаж из магазина
        """
        try:
            from app.database.connection import get_db_connection
            import sqlite3
            
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        ss.id,
                        ss.sale_date,
                        ss.created_at,
                        ss.final_amount,
                        ss.paid_amount,
                        ss.payment_method,
                        ss.comment,
                        u1.username as manager_name,
                        u2.username as master_name
                    FROM shop_sales ss
                    LEFT JOIN users u1 ON ss.manager_id = u1.id
                    LEFT JOIN users u2 ON ss.master_id = u2.id
                    WHERE ss.customer_id = ?
                    ORDER BY ss.created_at DESC, ss.sale_date DESC
                    LIMIT ?
                ''', (customer_id, limit))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении продаж из магазина для клиента {customer_id}: {e}")
            return []
    
    @staticmethod
    def get_customer_all_sales(customer_id: int, limit: int = 100) -> List[Dict]:
        """
        Получает все продажи клиента (из заявок и магазина), объединенные в один список.
        
        Args:
            customer_id: ID клиента
            limit: Максимальное количество продаж
            
        Returns:
            Список продаж с указанием источника (заявка или магазин)
        """
        try:
            from app.database.connection import get_db_connection
            from app.database.queries.order_queries import OrderQueries
            import sqlite3
            
            all_sales = []
            
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # 1. Получаем продажи из заявок (только те, где есть услуги или товары)
                cursor.execute('''
                    SELECT 
                        o.id,
                        o.order_id,
                        o.created_at,
                        u2.username as master_name,
                        (SELECT COALESCE(SUM(price * quantity), 0) FROM order_services WHERE order_id = o.id) AS services_total,
                        (SELECT COALESCE(SUM(price * quantity), 0) FROM order_parts WHERE order_id = o.id) AS parts_total,
                        (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE order_id = o.id) AS paid_amount
                    FROM orders o
                    LEFT JOIN users u2 ON o.master_id = u2.id
                    WHERE o.customer_id = ? 
                      AND (o.hidden = 0 OR o.hidden IS NULL)
                      AND (
                          EXISTS(SELECT 1 FROM order_services WHERE order_id = o.id)
                          OR EXISTS(SELECT 1 FROM order_parts WHERE order_id = o.id)
                      )
                    ORDER BY o.created_at DESC
                    LIMIT ?
                ''', (customer_id, limit))
                
                order_rows = cursor.fetchall()
                for row in order_rows:
                    order_dict = dict(row)
                    all_sales.append({
                        'sale_type': 'order',
                        'id': order_dict['id'],
                        'reference_id': order_dict['order_id'],
                        'date': order_dict['created_at'],
                        'services_total': float(order_dict['services_total'] or 0),
                        'parts_total': float(order_dict['parts_total'] or 0),
                        'total_amount': float(order_dict['services_total'] or 0) + float(order_dict['parts_total'] or 0),
                        'paid_amount': float(order_dict['paid_amount'] or 0),
                        'master_name': order_dict['master_name'],
                        'source_label': f"Заявка #{order_dict['id']}"
                    })
                
                # 2. Получаем продажи из магазина
                # Сначала получаем имя клиента для поиска по customer_name, если customer_id NULL
                cursor.execute('SELECT name FROM customers WHERE id = ?', (customer_id,))
                customer_row = cursor.fetchone()
                customer_name = customer_row[0] if customer_row else None
                
                # Формируем условие WHERE в зависимости от наличия customer_name
                if customer_name:
                    where_clause = "WHERE ss.customer_id = ? OR (ss.customer_id IS NULL AND ss.customer_name = ?)"
                    params = [customer_id, customer_name, limit]
                else:
                    where_clause = "WHERE ss.customer_id = ?"
                    params = [customer_id, limit]
                
                cursor.execute(f'''
                    SELECT 
                        ss.id,
                        ss.sale_date,
                        ss.created_at,
                        ss.final_amount,
                        ss.paid_amount,
                        ss.customer_id,
                        ss.customer_name,
                        u2.username as master_name,
                        (SELECT COALESCE(SUM(CASE WHEN item_type = 'service' THEN price * quantity ELSE 0 END), 0) 
                         FROM shop_sale_items WHERE shop_sale_id = ss.id) AS services_total,
                        (SELECT COALESCE(SUM(CASE WHEN item_type = 'part' THEN price * quantity ELSE 0 END), 0) 
                         FROM shop_sale_items WHERE shop_sale_id = ss.id) AS parts_total
                    FROM shop_sales ss
                    LEFT JOIN users u2 ON ss.master_id = u2.id
                    {where_clause}
                    ORDER BY ss.created_at DESC, ss.sale_date DESC
                    LIMIT ?
                ''', params)
                
                shop_rows = cursor.fetchall()
                for row in shop_rows:
                    shop_dict = dict(row)
                    sale_date = shop_dict['sale_date'] or shop_dict['created_at']
                    all_sales.append({
                        'sale_type': 'shop',
                        'id': shop_dict['id'],
                        'reference_id': shop_dict['id'],
                        'date': sale_date,
                        'services_total': float(shop_dict['services_total'] or 0),
                        'parts_total': float(shop_dict['parts_total'] or 0),
                        'total_amount': float(shop_dict['final_amount'] or 0),
                        'paid_amount': float(shop_dict['paid_amount'] or 0),
                        'master_name': shop_dict['master_name'],
                        'source_label': f"Магазин (чек #{shop_dict['id']})"
                    })
                
                # 3. Сортируем все продажи по дате (новые сверху)
                all_sales.sort(key=lambda x: x['date'] or '', reverse=True)
                
                # 4. Ограничиваем общее количество
                logger.info(f"Найдено продаж для клиента {customer_id}: {len(all_sales)} (заявки: {len(order_rows)}, магазин: {len(shop_rows)})")
                return all_sales[:limit]
                
        except Exception as e:
            logger.error(f"Ошибка при получении всех продаж клиента {customer_id}: {e}", exc_info=True)
            logger.error(f"Ошибка при получении всех продаж клиента {customer_id}: {e}")
            return []
    
    @staticmethod
    def get_customers_list(
        search_query: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
        sort_by: str = 'name',
        sort_order: str = 'ASC'
    ) -> Paginator:
        """
        Получает список клиентов с пагинацией.
        
        Args:
            search_query: Поисковый запрос
            page: Номер страницы
            per_page: Количество элементов на странице
            sort_by: Поле для сортировки
            sort_order: Направление сортировки
            
        Returns:
            Paginator с клиентами
        """
        result = CustomerQueries.get_customers_with_details(
            search_query=search_query,
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
    def search_customers(query: str, limit: int = 10) -> List[Dict]:
        """
        Быстрый поиск клиентов по имени, телефону или email.
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            Список клиентов
        """
        return CustomerQueries.search_customers(query, limit)
    
    @staticmethod
    def get_customer_statistics(customer_id: int) -> Dict:
        """
        Получает статистику клиента.
        
        Args:
            customer_id: ID клиента
            
        Returns:
            Словарь со статистикой
        """
        if not customer_id or customer_id <= 0:
            raise ValidationError("Неверный ID клиента")
        
        return CustomerQueries.get_customer_statistics(customer_id)
    
    @staticmethod
    def create_customer(data: Dict) -> Customer:
        """
        Создает нового клиента.
        
        Args:
            data: Словарь с данными клиента
            
        Returns:
            Созданный Customer
            
        Raises:
            ValidationError: Если данные невалидны
            DatabaseError: Если произошла ошибка БД
        """
        # Валидация
        validated_data = validate_customer_data(data)
        
        try:
            from app.database.connection import get_db_connection
            import sqlite3
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO customers (name, phone, email, created_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    validated_data['name'],
                    validated_data['phone'],
                    validated_data.get('email', '')
                ))
                conn.commit()
                
                customer_id = cursor.lastrowid
                
                if not customer_id:
                    raise DatabaseError("Не удалось создать клиента")
                
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
                                description=f"Автоматически сгенерирован пароль портала для клиента {validated_data['name']}",
                                details={
                                    'customer_id': customer_id,
                                    'customer_name': validated_data['name'],
                                    'customer_phone': validated_data['phone'],
                                    'generated_password': generated_password,
                                    'note': 'Пароль сохранен в захешированном виде. При первом входе клиент должен сменить пароль.'
                                }
                            )
                        except Exception as e:
                            logger.warning(f"Не удалось сохранить пароль в action_logs: {e}")
                except Exception as e:
                    logger.warning(f"Не удалось автоматически установить пароль портала для клиента {customer_id}: {e}")
                
                # Очищаем кэш
                clear_cache(key_prefix='customer')
                
                customer = Customer.get_by_id(customer_id)
                if not customer:
                    raise DatabaseError("Клиент создан, но не найден")
                
                # Логируем создание клиента
                try:
                    from flask_login import current_user
                    user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                    username = current_user.username if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='create',
                        entity_type='customer',
                        entity_id=customer_id,
                        details={
                            'Имя': customer.name,
                            'Телефон': customer.phone,
                            'Email': customer.email
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать создание клиента: {e}")
                
                return customer
        except sqlite3.IntegrityError as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            logger.error(f"Ошибка БД при создании клиента: {e}")
            raise ValidationError(error_msg)
        except sqlite3.Error as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            logger.error(f"Ошибка БД при создании клиента: {e}")
            raise DatabaseError(error_msg)
        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при создании клиента: {e}")
            raise DatabaseError(f"Ошибка при создании клиента: {e}")
    
    @staticmethod
    def update_customer(customer_id: int, data: Dict) -> bool:
        """
        Обновляет данные клиента.
        
        Args:
            customer_id: ID клиента
            data: Словарь с новыми данными
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если клиент не найден
            DatabaseError: Если произошла ошибка БД
        """
        if not customer_id or customer_id <= 0:
            raise ValidationError("Неверный ID клиента")
        
        # Проверяем, существует ли клиент
        customer = CustomerService.get_customer(customer_id)
        if not customer:
            raise NotFoundError(f"Клиент с ID {customer_id} не найден")
        
        # Сохраняем старые значения для лога
        old_values = {
            'name': customer.name,
            'phone': customer.phone,
            'email': customer.email or ''
        }
        
        # Валидация
        validated_data = validate_customer_data(data)
        
        try:
            from app.database.connection import get_db_connection
            import sqlite3
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE customers
                    SET name = ?, phone = ?, email = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    validated_data['name'],
                    validated_data['phone'],
                    validated_data.get('email', ''),
                    customer_id
                ))
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Клиент с ID {customer_id} не найден")
                
                # Очищаем кэш
                clear_cache(key_prefix='customer')
                
                # Логируем обновление клиента
                try:
                    from flask_login import current_user
                    user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                    username = current_user.username if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                    
                    new_values = {
                        'name': validated_data['name'],
                        'phone': validated_data['phone'],
                        'email': validated_data.get('email', '')
                    }
                    
                    # Определяем измененные поля
                    changed_fields = {}
                    for key in ['name', 'phone', 'email']:
                        if old_values.get(key) != new_values.get(key):
                            changed_fields[key] = {
                                'old': old_values.get(key),
                                'new': new_values.get(key)
                            }
                    
                    if changed_fields:
                        ActionLogService.log_action(
                            user_id=user_id,
                            username=username,
                            action_type='update',
                            entity_type='customer',
                            entity_id=customer_id,
                            details={
                                'field': 'customer_data',
                                'changes': changed_fields
                            }
                        )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать обновление клиента: {e}")
                
                return True
        except sqlite3.IntegrityError as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            logger.error(f"Ошибка БД при обновлении клиента {customer_id}: {e}")
            raise ValidationError(error_msg)
        except sqlite3.Error as e:
            from app.utils.db_error_translator import translate_db_error
            error_msg = translate_db_error(e)
            logger.error(f"Ошибка БД при обновлении клиента {customer_id}: {e}")
            raise DatabaseError(error_msg)
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обновлении клиента {customer_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении клиента: {e}")

