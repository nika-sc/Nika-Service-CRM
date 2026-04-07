"""
Миграция 002: Дополнительные индексы для оптимизации.

Добавляет индексы для улучшения производительности запросов.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 002_add_indexes: добавление дополнительных индексов")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Дополнительные индексы для таблицы orders
        # (основные уже созданы в 001_initial)
        # Добавляем только те, которые могут быть полезны для оптимизации
        
        # Индекс для поиска по дате обновления
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_updated_at 
            ON orders(updated_at)
        ''')
        
        # Составной индекс для фильтрации по статусу и дате создания
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_status_created_at 
            ON orders(status_id, created_at)
        ''')
        
        # Составной индекс для фильтрации по скрытости и дате создания
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_hidden_created_at 
            ON orders(hidden, created_at)
        ''')
        
        # Индекс для поиска устройств по серийному номеру
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_devices_serial_number 
            ON devices(serial_number)
        ''')
        
        # Индекс для поиска клиентов по email
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_customers_email 
            ON customers(email)
        ''')
        
        # Составной индекс для поиска клиентов по имени и телефону
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_customers_name_phone 
            ON customers(name, phone)
        ''')
        
        # Индекс для поиска запчастей по категории и остатку
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_parts_category_stock 
            ON parts(category, stock_quantity)
        ''')
        
        # Индекс для поиска услуг по умолчанию
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_services_is_default 
            ON services(is_default)
        ''')
        
        conn.commit()
        logger.info("Миграция 002_add_indexes успешно применена")


def down():
    """Откатывает миграцию."""
    logger.info("Откат миграции 002_add_indexes: удаление дополнительных индексов")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        indexes = [
            'idx_orders_updated_at',
            'idx_orders_status_created_at',
            'idx_orders_hidden_created_at',
            'idx_devices_serial_number',
            'idx_customers_email',
            'idx_customers_name_phone',
            'idx_parts_category_stock',
            'idx_services_is_default'
        ]
        
        for index_name in indexes:
            try:
                cursor.execute(f'DROP INDEX IF EXISTS {index_name}')
                logger.info(f"Индекс {index_name} удален")
            except Exception as e:
                logger.warning(f"Не удалось удалить индекс {index_name}: {e}")
        
        conn.commit()
        logger.info("Миграция 002_add_indexes откачена")

