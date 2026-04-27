"""
Сервис для логирования действий пользователей.
"""
from typing import Optional, Dict, List, Any
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.error_handlers import handle_service_error
from app.utils.pagination import Paginator
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Кеш: есть ли колонка description в action_logs (PRAGMA при каждой записи не нужен)
_has_description_column: Optional[bool] = None


def _check_has_description_column(cursor) -> bool:
    """Проверяет наличие колонки description (с кешированием)."""
    global _has_description_column
    if _has_description_column is None:
        cursor.execute("PRAGMA table_info(action_logs)")
        columns = [col[1] for col in cursor.fetchall()]
        _has_description_column = 'description' in columns
    return _has_description_column


class ActionLogService:
    """Сервис для логирования действий пользователей."""
    
    @staticmethod
    @handle_service_error
    def log_action(
        user_id: Optional[int],
        username: Optional[str],
        action_type: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Логирует действие пользователя.
        
        Args:
            user_id: ID пользователя
            username: Имя пользователя
            action_type: Тип действия (create, update, delete, view, etc.)
            entity_type: Тип сущности (order, customer, part, etc.)
            entity_id: ID сущности
            description: Описание действия
            details: Дополнительные детали (JSON)
            
        Returns:
            ID созданной записи лога
        """
        if not action_type or not entity_type:
            raise ValidationError("Тип действия и тип сущности обязательны")
        
        try:
            import json
            from app.utils.datetime_utils import get_moscow_now_str
            # Используем московское время (UTC+3)
            current_time = get_moscow_now_str()
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                has_description = _check_has_description_column(cursor)
                
                if has_description:
                    cursor.execute('''
                        INSERT INTO action_logs 
                        (user_id, username, action_type, entity_type, entity_id, description, details, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        username,
                        action_type,
                        entity_type,
                        entity_id,
                        description,
                        json.dumps(details, default=str) if details else None,
                        current_time
                    ))
                else:
                    # Если поля description нет, сохраняем его в details (копия, без мутации оригинала)
                    details_to_save = dict(details) if details else {}
                    if description:
                        details_to_save['description'] = description
                    cursor.execute('''
                        INSERT INTO action_logs 
                        (user_id, username, action_type, entity_type, entity_id, details, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        username,
                        action_type,
                        entity_type,
                        entity_id,
                        json.dumps(details_to_save, default=str) if details_to_save else None,
                        current_time
                    ))
                conn.commit()
                log_id = cursor.lastrowid
                logger.info(f"Действие залогировано: {action_type} {entity_type} {entity_id} пользователем {username}")
                return log_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при логировании действия: {e}")
            raise DatabaseError(f"Ошибка при логировании действия: {e}")
    
    @staticmethod
    @handle_service_error
    def get_action_logs(
        user_id: Optional[int] = None,
        action_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
        exclude_system_actions: bool = True
    ) -> Paginator:
        """
        Получает логи действий с фильтрацией.

        Args:
            user_id: Фильтр по пользователю
            action_type: Фильтр по типу действия (регистронезависимый)
            entity_type: Фильтр по типу сущности (регистронезависимый)
            entity_id: Фильтр по ID сущности
            date_from: Дата начала
            date_to: Дата окончания
            search_query: Поисковый запрос для текста описания
            page: Номер страницы
            per_page: Количество элементов на странице
            exclude_system_actions: Исключить системные операции (calculate, clear, backup, restore)

        Returns:
            Paginator с логами
        """
        offset = (page - 1) * per_page
        where_clauses = []
        params = []
        
        if user_id:
            where_clauses.append('al.user_id = ?')
            params.append(user_id)
        
        if action_type:
            # Регистронезависимый поиск по типу действия
            where_clauses.append('LOWER(al.action_type) = LOWER(?)')
            params.append(action_type)
        
        if entity_type:
            # Регистронезависимый поиск по типу сущности
            where_clauses.append('LOWER(al.entity_type) = LOWER(?)')
            params.append(entity_type)
        
        if entity_id:
            where_clauses.append('al.entity_id = ?')
            params.append(entity_id)
        
        if date_from:
            where_clauses.append('DATE(al.created_at) >= DATE(?)')
            params.append(date_from)
        
        if date_to:
            where_clauses.append('DATE(al.created_at) <= DATE(?)')
            params.append(date_to)

        # Исключаем системные действия по умолчанию
        if exclude_system_actions:
            system_actions = ['calculate', 'clear', 'backup', 'restore']
            system_entities = ['cache', 'backup', 'report']
            where_clauses.append('LOWER(al.action_type) NOT IN ({})'.format(','.join('?' * len(system_actions))))
            params.extend(system_actions)
            where_clauses.append('LOWER(al.entity_type) NOT IN ({})'.format(','.join('?' * len(system_entities))))
            params.extend(system_entities)

        # Поиск по тексту (в details JSON и username; description и entity_name вычисляются при отображении)
        if search_query:
            search_condition = '(al.details LIKE ? OR al.username LIKE ?)'
            where_clauses.append(search_condition)
            search_param = f'%{search_query}%'
            params.extend([search_param, search_param])

        where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        try:
            import json
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Подсчет общего количества
                count_query = f'''
                    SELECT COUNT(*)
                    FROM action_logs AS al
                    {where_sql}
                '''
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Получение данных
                query = f'''
                    SELECT 
                        al.*
                    FROM action_logs AS al
                    {where_sql}
                    ORDER BY al.created_at DESC
                    LIMIT ? OFFSET ?
                '''
                params.extend([per_page, offset])
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                items = []
                for row in rows:
                    item = dict(row)
                    # Парсим details если есть
                    if item.get('details'):
                        try:
                            item['details'] = json.loads(item['details'])
                        except (json.JSONDecodeError, TypeError):
                            pass
                    
                    # Получаем реальные данные по сущности
                    entity_type = item.get('entity_type')
                    entity_id = item.get('entity_id')
                    entity_name = None
                    entity_url = None
                    details = item.get('details', {}) if isinstance(item.get('details'), dict) else {}
                    
                    if entity_type and entity_id:
                        try:
                            if entity_type == 'order':
                                cursor.execute('''
                                    SELECT o.id, o.order_id, c.name AS customer_name
                                    FROM orders o
                                    LEFT JOIN customers c ON c.id = o.customer_id
                                    WHERE o.id = ?
                                ''', (entity_id,))
                                order_row = cursor.fetchone()
                                if order_row:
                                    # Используем числовой id для отображения номера заявки
                                    entity_name = f"Заявка #{order_row['id']}"
                                    if order_row['customer_name']:
                                        entity_name += f" ({order_row['customer_name']})"
                                    # Используем UUID (order_id) для ссылки, а не числовой id
                                    entity_url = f"/order/{order_row['order_id']}"
                            
                            elif entity_type == 'customer':
                                cursor.execute('''
                                    SELECT id, name, phone
                                    FROM customers
                                    WHERE id = ?
                                ''', (entity_id,))
                                customer_row = cursor.fetchone()
                                if customer_row:
                                    entity_name = customer_row['name']
                                    if customer_row['phone']:
                                        entity_name += f" ({customer_row['phone']})"
                                    entity_url = f"/clients/{customer_row['id']}"
                            
                            elif entity_type == 'part':
                                cursor.execute('''
                                    SELECT id, name, part_number
                                    FROM parts
                                    WHERE id = ?
                                ''', (entity_id,))
                                part_row = cursor.fetchone()
                                if part_row:
                                    entity_name = part_row['name']
                                    if part_row['part_number']:
                                        entity_name += f" (арт. {part_row['part_number']})"
                                    entity_url = f"/warehouse/parts/{part_row['id']}"
                            
                            elif entity_type == 'device':
                                cursor.execute('''
                                    SELECT d.id, dt.name AS device_type, db.name AS device_brand, d.serial_number
                                    FROM devices d
                                    LEFT JOIN device_types dt ON dt.id = d.device_type_id
                                    LEFT JOIN device_brands db ON db.id = d.device_brand_id
                                    WHERE d.id = ?
                                ''', (entity_id,))
                                device_row = cursor.fetchone()
                                if device_row:
                                    parts = []
                                    if device_row['device_type']:
                                        parts.append(device_row['device_type'])
                                    if device_row['device_brand']:
                                        parts.append(device_row['device_brand'])
                                    if device_row['serial_number']:
                                        parts.append(f"S/N: {device_row['serial_number']}")
                                    entity_name = " / ".join(parts) if parts else f"Устройство #{entity_id}"
                                    # Ссылка на историю устройства
                                    entity_url = f"/device/{entity_id}"
                            
                            elif entity_type == 'user':
                                cursor.execute('''
                                    SELECT id, username, role
                                    FROM users
                                    WHERE id = ?
                                ''', (entity_id,))
                                user_row = cursor.fetchone()
                                if user_row:
                                    entity_name = user_row['username']
                                    if user_row['role']:
                                        entity_name += f" ({user_row['role']})"
                                    entity_url = None
                            
                            elif entity_type == 'device_type':
                                cursor.execute('SELECT id, name FROM device_types WHERE id = ?', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    entity_name = f"Тип устройства: {row['name']}"
                                    entity_url = "/settings#device-data"
                            
                            elif entity_type == 'device_brand':
                                cursor.execute('SELECT id, name FROM device_brands WHERE id = ?', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    entity_name = f"Бренд: {row['name']}"
                                    entity_url = "/settings#device-data"
                            
                            elif entity_type == 'symptom':
                                cursor.execute('SELECT id, name FROM symptoms WHERE id = ?', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    entity_name = f"Тег неисправности: {row['name']}"
                                    entity_url = "/settings#device-data"
                            
                            elif entity_type == 'appearance_tag':
                                cursor.execute('SELECT id, name FROM appearance_tags WHERE id = ?', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    entity_name = f"Тег внешнего вида: {row['name']}"
                                    entity_url = "/settings#device-data"
                            
                            elif entity_type == 'service':
                                cursor.execute('SELECT id, name FROM services WHERE id = ?', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    entity_name = f"Услуга: {row['name']}"
                                    entity_url = "/settings#services"
                            
                            elif entity_type == 'order_status':
                                cursor.execute('SELECT id, name, code FROM order_statuses WHERE id = ?', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    entity_name = f"Статус: {row['name']} ({row['code']})"
                                    entity_url = "/settings#statuses"
                            
                            elif entity_type == 'general_settings':
                                entity_name = "Настройки организации"
                                entity_url = "/settings#general"
                            
                            elif entity_type == 'print_template':
                                # Получаем тип шаблона из details
                                template_type = details.get('template_type', '') if isinstance(details, dict) else ''
                                template_names = {
                                    'customer': 'Шаблон квитанции для клиента',
                                    'workshop': 'Шаблон для мастерской',
                                    'warranty': 'Гарантийный талон'
                                }
                                entity_name = template_names.get(template_type, 'Шаблон печати')
                                entity_url = "/settings#print-templates"
                            
                            elif entity_type == 'shop_sale':
                                cursor.execute('SELECT id, final_amount, customer_name FROM shop_sales WHERE id = ?', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    entity_name = f"Продажа №{row['id']}"
                                    if row['customer_name']:
                                        entity_name += f" ({row['customer_name']})"
                                    if row['final_amount']:
                                        entity_name += f" — {row['final_amount']:.0f} ₽"
                                    entity_url = f"/shop/sale/{row['id']}"
                                else:
                                    # Объект удалён, но ссылку всё равно создаём
                                    entity_name = f"Продажа №{entity_id} (удалена)"
                                    entity_url = f"/shop/sale/{entity_id}"
                            
                            elif entity_type == 'cash_transaction':
                                cursor.execute('''
                                    SELECT ct.id, ct.amount, ct.transaction_type, tc.name as category_name
                                    FROM cash_transactions ct
                                    LEFT JOIN transaction_categories tc ON ct.category_id = tc.id
                                    WHERE ct.id = ?
                                ''', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    tx_type = "Приход" if row['transaction_type'] == 'income' else "Расход"
                                    entity_name = f"Касса №{row['id']}: {tx_type} {row['amount']:.0f} ₽"
                                    if row['category_name']:
                                        entity_name += f" ({row['category_name']})"
                                    entity_url = f"/finance/cash"
                                else:
                                    # Объект удалён
                                    entity_name = f"Касса №{entity_id} (удалена)"
                                    entity_url = f"/finance/cash"
                            
                            elif entity_type == 'transaction_category':
                                cursor.execute('SELECT id, name, type FROM transaction_categories WHERE id = ?', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    cat_type = "доход" if row['type'] == 'income' else "расход"
                                    entity_name = f"Категория: {row['name']} ({cat_type})"
                                    entity_url = f"/finance/categories"
                                else:
                                    entity_name = f"Категория №{entity_id} (удалена)"
                                    entity_url = f"/finance/categories"
                            
                            elif entity_type == 'payment':
                                cursor.execute('''
                                    SELECT p.id, p.amount, p.payment_type, o.id as order_id, o.order_id as order_uuid
                                    FROM payments p
                                    LEFT JOIN orders o ON o.id = p.order_id
                                    WHERE p.id = ?
                                ''', (entity_id,))
                                row = cursor.fetchone()
                                if row:
                                    payment_type = "Наличные" if row['payment_type'] == 'cash' else "Карта" if row['payment_type'] == 'card' else "Перевод" if row['payment_type'] == 'transfer' else row['payment_type']
                                    entity_name = f"Оплата №{row['id']}: {row['amount']:.0f} ₽ ({payment_type})"
                                    if row['order_id']:
                                        entity_name += f" — Заявка #{row['order_id']}"
                                    # Ссылка на чек оплаты
                                    entity_url = f"/finance/payment/{row['id']}"
                                    
                                    if isinstance(details, dict):
                                        details.setdefault('payment_id', row['id'])
                                        if row['order_id']:
                                            details.setdefault('order_id', row['order_id'])
                                        if row['order_uuid']:
                                            details.setdefault('order_uuid', row['order_uuid'])
                                else:
                                    # Объект удалён
                                    entity_name = f"Оплата №{entity_id} (удалена)"
                                    entity_url = None
                            
                        except Exception as e:
                            logger.warning(f"Не удалось получить данные для {entity_type} #{entity_id}: {e}")
                    
                    # Если не удалось получить название из БД, пробуем использовать details (полезно для удалённых сущностей)
                    if not entity_name and details:
                        name_from_details = details.get('name')
                        amount_from_details = details.get('amount') or details.get('final_amount')
                        if name_from_details:
                            if entity_type == 'device_type':
                                entity_name = f"Тип устройства: {name_from_details}"
                            elif entity_type == 'device_brand':
                                entity_name = f"Бренд: {name_from_details}"
                            elif entity_type == 'symptom':
                                entity_name = f"Тег неисправности: {name_from_details}"
                            elif entity_type == 'appearance_tag':
                                entity_name = f"Тег внешнего вида: {name_from_details}"
                            elif entity_type == 'service':
                                entity_name = f"Услуга: {name_from_details}"
                            elif entity_type == 'shop_sale':
                                entity_name = f"Продажа №{entity_id}"
                                if amount_from_details:
                                    entity_name += f" — {amount_from_details:.0f} ₽"
                            elif entity_type == 'cash_transaction':
                                tx_type = details.get('transaction_type', '')
                                tx_label = "Приход" if tx_type == 'income' else "Расход" if tx_type == 'expense' else ""
                                entity_name = f"Касса №{entity_id}"
                                if tx_label and amount_from_details:
                                    entity_name += f": {tx_label} {amount_from_details:.0f} ₽"
                            elif entity_type == 'transaction_category':
                                entity_name = f"Категория: {name_from_details}"
                            else:
                                entity_name = f"{entity_type}: {name_from_details}"
                        elif amount_from_details:
                            # Если есть сумма, но нет имени
                            if entity_type == 'shop_sale':
                                entity_name = f"Продажа №{entity_id} — {amount_from_details:.0f} ₽"
                            elif entity_type == 'cash_transaction':
                                entity_name = f"Касса №{entity_id} — {amount_from_details:.0f} ₽"
                    
                    # Если всё ещё не удалось получить человекочитаемое название, используем дефолтное с русскими названиями
                    if not entity_name:
                        entity_type_labels = {
                            'order': 'Заявка',
                            'customer': 'Клиент',
                            'device': 'Устройство',
                            'part': 'Товар',
                            'service': 'Услуга',
                            'payment': 'Оплата',
                            'comment': 'Комментарий',
                            'shop_sale': 'Продажа',
                            'cash_transaction': 'Касса',
                            'transaction_category': 'Категория',
                            'stock_movement': 'Движение склада',
                            'purchase': 'Закупка',
                            'user': 'Пользователь',
                            'device_type': 'Тип устройства',
                            'device_brand': 'Бренд',
                            'device_model': 'Модель',
                            'symptom': 'Тег неисправности',
                            'appearance_tag': 'Тег внешнего вида',
                            'order_status': 'Статус',
                            'print_template': 'Шаблон печати',
                        }
                        type_label = entity_type_labels.get(entity_type, entity_type)
                        entity_name = f"{type_label} №{entity_id}" if entity_id else type_label
                    
                    # Если нет URL, создаём fallback ссылку для известных типов сущностей
                    if not entity_url and entity_id:
                        fallback_urls = {
                            'order': f"/all_orders",  # Заявки могут быть в списке
                            'customer': f"/clients/{entity_id}",
                            'part': f"/warehouse/parts/{entity_id}",
                            'shop_sale': f"/shop/sale/{entity_id}",
                            'cash_transaction': f"/finance/cash",
                            'transaction_category': f"/finance/categories",
                        }
                        entity_url = fallback_urls.get(entity_type)
                    
                    item['entity_name'] = entity_name
                    item['entity_url'] = entity_url

                    # Улучшаем описание для большей человекочитаемости
                    action_type = item.get('action_type', '')
                    entity_type = item.get('entity_type', '')
                    description = item.get('description', '')

                    # Генерируем более понятные описания на основе типа действия и сущности
                    if not description or len(description.strip()) < 5:
                        # Если описание слишком короткое или отсутствует, генерируем новое
                        if action_type == 'create':
                            if entity_type == 'order':
                                description = f"Создана заявка {entity_name}"
                            elif entity_type == 'customer':
                                description = f"Создан клиент {entity_name}"
                            elif entity_type == 'device':
                                description = f"Добавлено устройство {entity_name}"
                            elif entity_type == 'user':
                                description = f"Создан пользователь {entity_name}"
                            elif entity_type == 'purchase':
                                description = "Создана закупка"
                            elif entity_type in ['device_type', 'device_brand', 'symptom', 'appearance_tag', 'service']:
                                description = f"Добавлен справочник: {entity_name}"
                            elif entity_type == 'transaction_category':
                                description = f"Создана категория операций: {entity_name}"
                            else:
                                description = f"Создан объект: {entity_name}"

                        elif action_type == 'update':
                            if entity_type == 'order':
                                description = f"Обновлена заявка {entity_name}"
                            elif entity_type == 'customer':
                                description = f"Обновлен клиент {entity_name}"
                            elif entity_type == 'device':
                                description = f"Обновлено устройство {entity_name}"
                            elif entity_type == 'user':
                                description = f"Обновлен пользователь {entity_name}"
                            elif entity_type == 'purchase':
                                description = "Обновлена закупка"
                            elif entity_type in ['device_type', 'device_brand', 'symptom', 'appearance_tag', 'service']:
                                description = f"Изменен справочник: {entity_name}"
                            elif entity_type == 'transaction_category':
                                description = f"Обновлена категория операций: {entity_name}"
                            else:
                                description = f"Обновлен объект: {entity_name}"

                        elif action_type == 'delete':
                            if entity_type == 'order':
                                description = f"Удалена заявка {entity_name}"
                            elif entity_type == 'customer':
                                description = f"Удален клиент {entity_name}"
                            elif entity_type == 'device':
                                description = f"Удалено устройство {entity_name}"
                            elif entity_type == 'user':
                                description = f"Удален пользователь {entity_name}"
                            elif entity_type == 'purchase':
                                description = "Удалена закупка"
                            elif entity_type in ['device_type', 'device_brand', 'symptom', 'appearance_tag', 'service']:
                                description = f"Удален справочник: {entity_name}"
                            elif entity_type == 'transaction_category':
                                description = f"Удалена категория операций: {entity_name}"
                            else:
                                description = f"Удален объект: {entity_name}"

                        elif action_type == 'add_payment':
                            description = f"Добавлена оплата к {entity_name}"
                        elif action_type == 'delete_payment':
                            description = f"Удалена оплата от {entity_name}"
                        elif action_type == 'add_service':
                            description = f"Добавлена услуга к {entity_name}"
                        elif action_type == 'remove_service':
                            description = f"Удалена услуга из {entity_name}"
                        elif action_type == 'add_part':
                            description = f"Добавлен товар к {entity_name}"
                        elif action_type == 'remove_part':
                            description = f"Удален товар из {entity_name}"
                        elif action_type == 'sell':
                            description = f"Продажа по {entity_name}"
                        elif action_type == 'create_transaction':
                            description = f"Кассовая операция: {entity_name}"
                        elif action_type == 'create_shop_sale':
                            description = f"Продажа в магазине: {entity_name}"
                        elif action_type == 'refund_shop_sale':
                            description = f"Возврат продажи: {entity_name}"
                        elif action_type == 'status_change':
                            description = f"Изменен статус {entity_name}"

                    # Сохраняем улучшенное описание
                    item['description'] = description

                    items.append(item)
                
                return Paginator(
                    items=items,
                    page=page,
                    per_page=per_page,
                    total=total
                )
        except Exception as e:
            logger.error(f"Ошибка при получении логов действий: {e}")
            return Paginator(items=[], page=page, per_page=per_page, total=0)
    
    @staticmethod
    @handle_service_error
    def get_entity_logs(entity_type: str, entity_id: int, limit: int = 50) -> List[Dict]:
        """
        Получает логи по конкретной сущности.
        
        Args:
            entity_type: Тип сущности
            entity_id: ID сущности
            limit: Максимальное количество записей
            
        Returns:
            Список логов
        """
        return ActionLogService.get_action_logs(
            entity_type=entity_type,
            entity_id=entity_id,
            page=1,
            per_page=limit
        ).items

