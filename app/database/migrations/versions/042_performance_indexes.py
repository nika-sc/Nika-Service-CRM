"""
Миграция 042: Индексы для оптимизации производительности.

Добавляет индексы для улучшения производительности запросов.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _index_exists(cursor, index_name: str) -> bool:
    """Проверяет существование индекса."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 042_performance_indexes")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Индексы для orders
        indexes = [
            ('idx_orders_status_created_at', 'orders', '(status_id, created_at)'),
            ('idx_orders_master_status', 'orders', '(master_id, status_id)'),
            ('idx_orders_manager_created', 'orders', '(manager_id, created_at)'),
            ('idx_orders_customer_created', 'orders', '(customer_id, created_at)'),
            
            # Индексы для order_comments
            ('idx_order_comments_order_created_desc', 'order_comments', '(order_id, created_at DESC)'),
            
            # Индексы для payments
            ('idx_payments_order_created', 'payments', '(order_id, created_at)'),
            ('idx_payments_status_created', 'payments', '(status, created_at)'),
            
            # Индексы для customers (поиск)
            ('idx_customers_name_phone', 'customers', '(name, phone)'),
        ]
        
        for index_name, table, columns in indexes:
            if not _index_exists(cursor, index_name):
                logger.info(f"Создание индекса {index_name}...")
                try:
                    cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table} {columns}')
                    logger.info(f"Индекс {index_name} создан")
                except Exception as e:
                    logger.warning(f"Не удалось создать индекс {index_name}: {e}")
            else:
                logger.info(f"Индекс {index_name} уже существует, пропускаем")
        
        conn.commit()
        logger.info("Миграция 042_performance_indexes успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 042_performance_indexes")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        indexes_to_drop = [
            'idx_orders_status_created_at',
            'idx_orders_master_status',
            'idx_orders_manager_created',
            'idx_orders_customer_created',
            'idx_order_comments_order_created_desc',
            'idx_payments_order_created',
            'idx_payments_status_created',
            'idx_customers_name_phone'
        ]
        
        for index_name in indexes_to_drop:
            if _index_exists(cursor, index_name):
                logger.info(f"Удаление индекса {index_name}...")
                cursor.execute(f'DROP INDEX IF EXISTS {index_name}')
                logger.info(f"Индекс {index_name} удален")
        
        conn.commit()
        logger.info("Миграция 042_performance_indexes откачена")
