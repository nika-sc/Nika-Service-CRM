"""
Модель заявки.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.base import BaseModel
from app.database.connection import get_db_connection
from app.utils.validators import validate_price
from app.utils.exceptions import ValidationError
import sqlite3
import logging

logger = logging.getLogger(__name__)


class Order(BaseModel):
    """
    Модель заявки.
    
    Атрибуты:
        id: ID заявки
        order_id: UUID заявки (уникальный)
        device_id: ID устройства
        customer_id: ID клиента
        manager_id: ID менеджера
        master_id: ID мастера
        status_id: ID статуса
        status: Код статуса (legacy)
        prepayment: Предоплата
        password: Пароль от устройства
        appearance: Внешний вид (текст, для обратной совместимости)
        comment: Комментарий
        symptom_tags: Теги симптомов (текст, для обратной совместимости)
        model: Модель устройства (текст, для обратной совместимости)
        model_id: ID модели устройства (FK к order_models, нормализованное поле)
        hidden: Скрыта ли заявка (0 - видима, 1 - скрыта)
        created_at: Дата создания
        updated_at: Дата обновления
    """
    
    @staticmethod
    def _not_deleted_clause(cursor, alias: str = 'o') -> str:
        """Фильтр мягко удаленных заявок (совместим со старыми БД)."""
        try:
            cursor.execute("PRAGMA table_info(orders)")
            columns = {row[1] for row in cursor.fetchall()}
            if 'is_deleted' in columns:
                return f" AND ({alias}.is_deleted = 0 OR {alias}.is_deleted IS NULL)"
        except Exception:
            pass
        return ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.id = kwargs.get('id')
        self.order_id = kwargs.get('order_id')
        self.device_id = kwargs.get('device_id')
        self.customer_id = kwargs.get('customer_id')
        self.manager_id = kwargs.get('manager_id')
        self.master_id = kwargs.get('master_id')
        self.status_id = kwargs.get('status_id')
        self.status = kwargs.get('status')
        self.status_code = kwargs.get('status_code')
        self.status_name = kwargs.get('status_name')
        self.status_color = kwargs.get('status_color')
        self.prepayment = kwargs.get('prepayment', '0')
        self.password = kwargs.get('password')
        self.appearance = kwargs.get('appearance')
        self.comment = kwargs.get('comment')
        self.symptom_tags = kwargs.get('symptom_tags')
        self.model = kwargs.get('model')
        self.model_id = kwargs.get('model_id')
        self.hidden = kwargs.get('hidden', 0)
        self.is_deleted = kwargs.get('is_deleted', 0)
        self.deleted_at = kwargs.get('deleted_at')
        self.deleted_by_id = kwargs.get('deleted_by_id')
        self.deleted_reason = kwargs.get('deleted_reason')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        
        # Связанные данные
        self.client_name = kwargs.get('client_name')
        self.phone = kwargs.get('phone')
        self.email = kwargs.get('email')
        self.serial_number = kwargs.get('serial_number')
        self.device_type_name = kwargs.get('device_type_name')
        self.device_brand_name = kwargs.get('device_brand_name')
        self.manager_name = kwargs.get('manager_name')
        self.master_name = kwargs.get('master_name')
    
    def validate(self) -> None:
        """
        Валидирует данные заявки.
        
        Raises:
            ValidationError: Если данные невалидны
        """
        errors = []
        
        # Валидация customer_id
        if not self.customer_id:
            errors.append("ID клиента обязателен")
        
        # Валидация device_id
        if not self.device_id:
            errors.append("ID устройства обязательно")
        
        # Валидация manager_id
        if not self.manager_id:
            errors.append("ID менеджера обязателен")
        
        # Валидация prepayment (если указана)
        if self.prepayment is not None:
            try:
                prepayment = float(self.prepayment) if isinstance(self.prepayment, str) else self.prepayment
                if prepayment < 0:
                    errors.append("Предоплата не может быть отрицательной")
            except (ValueError, TypeError):
                errors.append("Неверный формат предоплаты")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    @classmethod
    def get_by_id(cls, order_id: int) -> Optional['Order']:
        """
        Получает заявку по ID.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Order или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                not_deleted_clause = cls._not_deleted_clause(cursor, 'o')
                cursor.execute('''
                    SELECT 
                        o.*,
                        c.name AS client_name,
                        c.phone,
                        c.email,
                        d.serial_number,
                        dt.name AS device_type_name,
                        db.name AS device_brand_name,
                        mgr.name AS manager_name,
                        ms.name AS master_name,
                        os.code AS status_code,
                        os.name AS status_name,
                        os.color AS status_color
                    FROM orders AS o
                    JOIN customers AS c ON c.id = o.customer_id
                    JOIN devices AS d ON d.id = o.device_id
                    LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                    LEFT JOIN managers AS mgr ON mgr.id = o.manager_id
                    LEFT JOIN masters AS ms ON ms.id = o.master_id
                    LEFT JOIN order_statuses AS os ON os.id = o.status_id
                    WHERE o.id = ?
                ''' + not_deleted_clause, (order_id,))
                
                row = cursor.fetchone()
                if row:
                    return cls.from_dict(dict(row))
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении заявки {order_id}: {e}")
            return None
    
    @classmethod
    def get_by_uuid(cls, order_uuid: str) -> Optional['Order']:
        """
        Получает заявку по UUID.
        
        Args:
            order_uuid: UUID заявки
            
        Returns:
            Order или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                not_deleted_clause = cls._not_deleted_clause(cursor, 'o')
                # Используем LEFT JOIN для customers и devices, чтобы заявка находилась даже если связанные данные отсутствуют
                cursor.execute('''
                    SELECT 
                        o.*,
                        c.name AS client_name,
                        c.phone,
                        c.email,
                        d.serial_number,
                        dt.name AS device_type_name,
                        db.name AS device_brand_name,
                        mgr.name AS manager_name,
                        ms.name AS master_name,
                        os.code AS status_code,
                        os.name AS status_name,
                        os.color AS status_color
                    FROM orders AS o
                    LEFT JOIN customers AS c ON c.id = o.customer_id
                    LEFT JOIN devices AS d ON d.id = o.device_id
                    LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                    LEFT JOIN managers AS mgr ON mgr.id = o.manager_id
                    LEFT JOIN masters AS ms ON ms.id = o.master_id
                    LEFT JOIN order_statuses AS os ON os.id = o.status_id
                    WHERE o.order_id = ?
                ''' + not_deleted_clause, (order_uuid,))
                
                row = cursor.fetchone()
                if row:
                    logger.debug(f"Заявка найдена в БД: ID={row['id']}, UUID={row['order_id']}")
                    try:
                        # Преобразуем Row в словарь
                        row_dict = dict(row)
                        logger.debug(f"Преобразовано в словарь, ключи: {list(row_dict.keys())[:10]}")
                        order = cls.from_dict(row_dict)
                        logger.debug(f"Модель создана успешно: ID={order.id}, UUID={order.order_id}")
                        return order
                    except Exception as e:
                        logger.error(f"Ошибка при создании модели Order из словаря: {e}", exc_info=True)
                        # Пытаемся создать минимальную модель
                        try:
                            return cls(
                                id=row['id'],
                                order_id=row['order_id'],
                                customer_id=row.get('customer_id'),
                                device_id=row.get('device_id'),
                                manager_id=row.get('manager_id'),
                                master_id=row.get('master_id'),
                                status_id=row.get('status_id'),
                                client_name=row.get('client_name'),
                                phone=row.get('phone'),
                                email=row.get('email'),
                                serial_number=row.get('serial_number'),
                                device_type_name=row.get('device_type_name'),
                                device_brand_name=row.get('device_brand_name'),
                                manager_name=row.get('manager_name'),
                                master_name=row.get('master_name'),
                                status_code=row.get('status_code'),
                                status_name=row.get('status_name'),
                                status_color=row.get('status_color')
                            )
                        except Exception as e2:
                            logger.error(f"Ошибка при создании минимальной модели: {e2}", exc_info=True)
                            return None
                else:
                    # Проверяем, существует ли заявка вообще (даже без связанных данных)
                    not_deleted_simple = cls._not_deleted_clause(cursor, 'orders')
                    cursor.execute('''
                        SELECT id, order_id, customer_id, device_id
                        FROM orders
                        WHERE order_id = ?
                    ''' + not_deleted_simple, (order_uuid,))
                    simple_row = cursor.fetchone()
                    if simple_row:
                        logger.warning(f"Заявка с UUID {order_uuid} существует в БД (ID={simple_row['id']}), но не найдена через JOIN. Возможно, отсутствуют связанные данные (customer_id={simple_row['customer_id']}, device_id={simple_row['device_id']})")
                    else:
                        logger.warning(f"Заявка с UUID {order_uuid} не найдена в БД вообще")
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении заявки по UUID {order_uuid}: {e}", exc_info=True)
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует модель в словарь."""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'device_id': self.device_id,
            'customer_id': self.customer_id,
            'manager_id': self.manager_id,
            'master_id': self.master_id,
            'status_id': self.status_id,
            'status': self.status,
            'status_code': self.status_code,
            'status_name': self.status_name,
            'status_color': self.status_color,
            'prepayment': self.prepayment,
            'password': self.password,
            'appearance': self.appearance,
            'comment': self.comment,
            'symptom_tags': self.symptom_tags,
            'hidden': self.hidden,
            'is_deleted': self.is_deleted,
            'deleted_at': self.deleted_at,
            'deleted_by_id': self.deleted_by_id,
            'deleted_reason': self.deleted_reason,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'client_name': self.client_name,
            'phone': self.phone,
            'email': self.email,
            'serial_number': self.serial_number,
            'device_type_name': self.device_type_name,
            'device_brand_name': self.device_brand_name,
            'manager_name': self.manager_name,
            'master_name': self.master_name
        }

