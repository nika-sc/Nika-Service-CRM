"""
Сервис для работы с устройствами.
"""
from typing import Optional, List, Dict
from app.models.device import Device
from app.database.queries.device_queries import DeviceQueries
from app.utils.cache import cache_result, clear_cache
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.services.action_log_service import ActionLogService
import logging

logger = logging.getLogger(__name__)


class DeviceService:
    """Сервис для работы с устройствами."""
    
    @staticmethod
    @cache_result(timeout=300, key_prefix='device')
    def get_device(device_id: int) -> Optional[Device]:
        """
        Получает устройство по ID с кэшированием.
        
        Args:
            device_id: ID устройства
            
        Returns:
            Device или None
        """
        return Device.get_by_id(device_id)
    
    @staticmethod
    def get_customer_devices(customer_id: int) -> List[Device]:
        """
        Получает все устройства клиента.
        
        Args:
            customer_id: ID клиента
            
        Returns:
            Список устройств
        """
        return Device.get_by_customer_id(customer_id)
    
    @staticmethod
    def get_device_orders(device_id: int) -> List[Dict]:
        """
        Получает все заявки по устройству.
        
        Args:
            device_id: ID устройства
            
        Returns:
            Список заявок
        """
        if not device_id or device_id <= 0:
            raise ValidationError("Неверный ID устройства")
        
        return DeviceQueries.get_device_orders(device_id)
    
    @staticmethod
    def create_device(customer_id: int, device_type_id: int, device_brand_id: int, 
                     serial_number: str = None, password: str = None, 
                     symptom_tags: str = None, appearance_tags: str = None,
                     comment: str = None) -> Optional[Device]:
        """
        Создает новое устройство.
        
        Args:
            customer_id: ID клиента
            device_type_id: ID типа устройства
            device_brand_id: ID бренда устройства
            serial_number: Серийный номер
            password: Пароль от устройства (опционально)
            symptom_tags: Типичные неисправности (опционально)
            appearance_tags: Внешний вид и комплектация (опционально)
            comment: Комментарий (виден только сервисному центру) (опционально)
            
        Returns:
            Созданное Device или None
        """
        try:
            from app.database.connection import get_db_connection
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Проверяем, есть ли новые колонки в таблице
                cursor.execute("PRAGMA table_info(devices)")
                columns = [row[1] for row in cursor.fetchall()]
                
                has_new_columns = 'password' in columns and 'symptom_tags' in columns and 'appearance_tags' in columns
                has_comment = 'comment' in columns
                
                if has_new_columns and has_comment:
                    cursor.execute('''
                        INSERT INTO devices (customer_id, device_type_id, device_brand_id, serial_number, 
                                           password, symptom_tags, appearance_tags, comment, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (customer_id, device_type_id, device_brand_id, serial_number, 
                          password, symptom_tags, appearance_tags, comment))
                elif has_new_columns:
                    cursor.execute('''
                        INSERT INTO devices (customer_id, device_type_id, device_brand_id, serial_number, 
                                           password, symptom_tags, appearance_tags, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (customer_id, device_type_id, device_brand_id, serial_number, 
                          password, symptom_tags, appearance_tags))
                else:
                    cursor.execute('''
                        INSERT INTO devices (customer_id, device_type_id, device_brand_id, serial_number, created_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (customer_id, device_type_id, device_brand_id, serial_number))
                conn.commit()
                
                device_id = cursor.lastrowid
                
                # Очищаем кэш
                clear_cache(key_prefix='device')
                
                device = Device.get_by_id(device_id)
                
                # Логируем создание устройства
                try:
                    from flask_login import current_user
                    from app.database.queries.reference_queries import ReferenceQueries
                    from app.models.customer import Customer
                    
                    user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                    username = current_user.username if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                    
                    # Получаем названия для отображения
                    customer = Customer.get_by_id(customer_id)
                    customer_name = customer.name if customer else f'ID: {customer_id}'
                    
                    device_types = ReferenceQueries.get_device_types()
                    device_brands = ReferenceQueries.get_device_brands()
                    device_type_name = next((dt['name'] for dt in device_types if dt['id'] == device_type_id), f'ID: {device_type_id}')
                    device_brand_name = next((db['name'] for db in device_brands if db['id'] == device_brand_id), f'ID: {device_brand_id}')
                    
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='create',
                        entity_type='device',
                        entity_id=device_id,
                        details={
                            'Клиент': customer_name,
                            'Тип устройства': device_type_name,
                            'Бренд': device_brand_name,
                            'Серийный номер': serial_number or 'Не указан'
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать создание устройства: {e}")
                
                return device
        except Exception as e:
            logger.error(f"Ошибка при создании устройства: {e}")
            return None
    
    @staticmethod
    def update_device(device_id: int, device_type_id: int = None, 
                     device_brand_id: int = None, serial_number: str = None,
                     password: str = None, symptom_tags: str = None, 
                     appearance_tags: str = None, comment: str = None) -> bool:
        """
        Обновляет данные устройства.
        
        Args:
            device_id: ID устройства
            device_type_id: ID типа устройства (опционально)
            device_brand_id: ID бренда устройства (опционально)
            serial_number: Серийный номер (опционально)
            password: Пароль от устройства (опционально)
            symptom_tags: Типичные неисправности (опционально)
            appearance_tags: Внешний вид и комплектация (опционально)
            
        Returns:
            True если успешно, False в случае ошибки
        """
        try:
            from app.database.connection import get_db_connection
            
            # Получаем старое устройство для лога
            old_device = Device.get_by_id(device_id)
            if not old_device:
                return False
            
            # Проверяем, есть ли новые колонки в таблице
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(devices)")
                columns = [row[1] for row in cursor.fetchall()]
                has_new_columns = 'password' in columns and 'symptom_tags' in columns and 'appearance_tags' in columns
                has_comment = 'comment' in columns
            
            updates = []
            params = []
            changes = {}
            
            if device_type_id is not None:
                updates.append('device_type_id = ?')
                params.append(device_type_id)
                if old_device.device_type_id != device_type_id:
                    changes['device_type_id'] = {'old': old_device.device_type_id, 'new': device_type_id}
            
            if device_brand_id is not None:
                updates.append('device_brand_id = ?')
                params.append(device_brand_id)
                if old_device.device_brand_id != device_brand_id:
                    changes['device_brand_id'] = {'old': old_device.device_brand_id, 'new': device_brand_id}
            
            if serial_number is not None:
                updates.append('serial_number = ?')
                params.append(serial_number)
                if old_device.serial_number != serial_number:
                    changes['serial_number'] = {'old': old_device.serial_number, 'new': serial_number}
            
            if has_new_columns:
                if password is not None:
                    updates.append('password = ?')
                    params.append(password)
                
                if symptom_tags is not None:
                    updates.append('symptom_tags = ?')
                    params.append(symptom_tags)
                
                if appearance_tags is not None:
                    updates.append('appearance_tags = ?')
                    params.append(appearance_tags)
            
            if has_comment:
                if comment is not None:
                    updates.append('comment = ?')
                    params.append(comment)
            
            if not updates:
                return False
            
            params.append(device_id)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE devices
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                # Очищаем кэш
                clear_cache(key_prefix='device')
                
                if cursor.rowcount > 0 and changes:
                    # Логируем обновление устройства
                    try:
                        from flask_login import current_user
                        from app.database.queries.reference_queries import ReferenceQueries
                        
                        user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                        username = current_user.username if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                        
                        # Преобразуем changes в понятные названия
                        readable_changes = {}
                        device_types = ReferenceQueries.get_device_types()
                        device_brands = ReferenceQueries.get_device_brands()
                        
                        for key, value in changes.items():
                            if key == 'device_type_id':
                                old_name = next((dt['name'] for dt in device_types if dt['id'] == value.get('old')), f"ID: {value.get('old')}")
                                new_name = next((dt['name'] for dt in device_types if dt['id'] == value.get('new')), f"ID: {value.get('new')}")
                                readable_changes['Тип устройства'] = {'old': old_name, 'new': new_name}
                            elif key == 'device_brand_id':
                                old_name = next((db['name'] for db in device_brands if db['id'] == value.get('old')), f"ID: {value.get('old')}")
                                new_name = next((db['name'] for db in device_brands if db['id'] == value.get('new')), f"ID: {value.get('new')}")
                                readable_changes['Бренд'] = {'old': old_name, 'new': new_name}
                            elif key == 'serial_number':
                                readable_changes['Серийный номер'] = {'old': value.get('old') or 'Не указан', 'new': value.get('new') or 'Не указан'}
                        
                        ActionLogService.log_action(
                            user_id=user_id,
                            username=username,
                            action_type='update',
                            entity_type='device',
                            entity_id=device_id,
                            details={
                                'field': 'device_data',
                                'changes': readable_changes
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось залогировать обновление устройства: {e}")
                
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении устройства {device_id}: {e}")
            return False
    
    @staticmethod
    def delete_device(device_id: int) -> bool:
        """
        Удаляет устройство.
        
        Args:
            device_id: ID устройства
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если устройство не найдено
            DatabaseError: Если произошла ошибка БД или есть связанные заявки
        """
        if not device_id or device_id <= 0:
            raise ValidationError("Неверный ID устройства")
        
        # Проверяем существование устройства
        device = DeviceService.get_device(device_id)
        if not device:
            raise NotFoundError(f"Устройство с ID {device_id} не найдено")
        
        try:
            from app.database.connection import get_db_connection
            import sqlite3
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Включаем поддержку внешних ключей для SQLite
                cursor.execute('PRAGMA foreign_keys = ON')
                
                # Проверяем наличие связанных заявок
                cursor.execute('SELECT COUNT(*) FROM orders WHERE device_id = ?', (device_id,))
                orders_count = cursor.fetchone()[0]
                
                if orders_count > 0:
                    raise DatabaseError(
                        f"Невозможно удалить устройство: на него ссылаются {orders_count} заявок. "
                        f"Сначала удалите или измените связанные заявки."
                    )
                
                # Удаляем устройство
                cursor.execute('DELETE FROM devices WHERE id = ?', (device_id,))
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Устройство с ID {device_id} не найдено")
                
                # Очищаем кэш
                clear_cache(key_prefix='device')
                
                # Логируем удаление устройства
                try:
                    from flask_login import current_user
                    user_id = current_user.id if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                    username = current_user.username if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated else None
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='delete',
                        entity_type='device',
                        entity_id=device_id,
                        details={
                            'customer_id': device.customer_id,
                            'device_type_id': device.device_type_id,
                            'device_brand_id': device.device_brand_id,
                            'serial_number': device.serial_number
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать удаление устройства: {e}")
                
                return True
        except (ValidationError, NotFoundError, DatabaseError):
            raise
        except sqlite3.Error as e:
            error_msg = str(e)
            if 'FOREIGN KEY constraint failed' in error_msg:
                # Пытаемся получить количество связанных заявок для более понятного сообщения
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM orders WHERE device_id = ?', (device_id,))
                        orders_count = cursor.fetchone()[0]
                        raise DatabaseError(
                            f"Невозможно удалить устройство: на него ссылаются {orders_count} заявок. "
                            f"Сначала удалите или измените связанные заявки."
                        )
                except DatabaseError:
                    raise
                except Exception:
                    raise DatabaseError(
                        "Невозможно удалить устройство: на него ссылаются заявки. "
                        "Сначала удалите или измените связанные заявки."
                    )
            logger.error(f"Ошибка БД при удалении устройства {device_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при удалении устройства {device_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении устройства: {e}")

