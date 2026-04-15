"""
Скрипт для добавления индексов в базу данных для оптимизации запросов.
"""
import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def add_indexes(db_path='database/service_center.db'):
    """
    Добавляет индексы для оптимизации запросов.
    
    Args:
        db_path: Путь к базе данных
    """
    if not os.path.exists(db_path):
        logger.error(f"База данных не найдена: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Список индексов для создания
        indexes = [
            # Индексы для таблицы orders
            ("idx_orders_customer_id", "orders", "customer_id"),
            ("idx_orders_device_id", "orders", "device_id"),
            ("idx_orders_status_id", "orders", "status_id"),
            ("idx_orders_manager_id", "orders", "manager_id"),
            ("idx_orders_master_id", "orders", "master_id"),
            ("idx_orders_created_at", "orders", "created_at"),
            ("idx_orders_hidden", "orders", "hidden"),
            ("idx_orders_order_id", "orders", "order_id"),  # UUID для поиска
            
            # Индексы для таблицы customers
            ("idx_customers_phone", "customers", "phone"),  # Для поиска по телефону
            
            # Индексы для таблицы devices
            ("idx_devices_customer_id", "devices", "customer_id"),
            ("idx_devices_device_type_id", "devices", "device_type_id"),
            ("idx_devices_device_brand_id", "devices", "device_brand_id"),
            
            # Индексы для таблицы order_services
            ("idx_order_services_order_id", "order_services", "order_id"),
            ("idx_order_services_service_id", "order_services", "service_id"),
            
            # Индексы для таблицы order_parts
            ("idx_order_parts_order_id", "order_parts", "order_id"),
            ("idx_order_parts_part_id", "order_parts", "part_id"),
            
            # Индексы для таблицы payments
            ("idx_payments_order_id", "payments", "order_id"),
            ("idx_payments_payment_date", "payments", "payment_date"),
            
            # Индексы для таблицы order_comments
            ("idx_order_comments_order_id", "order_comments", "order_id"),
            ("idx_order_comments_created_at", "order_comments", "created_at"),
        ]
        
        created_count = 0
        skipped_count = 0
        error_count = 0
        
        for index_name, table_name, column_name in indexes:
            try:
                # Проверяем, существует ли индекс
                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='index' AND name=?
                ''', (index_name,))
                
                if cursor.fetchone():
                    logger.info(f"Индекс {index_name} уже существует, пропускаем")
                    skipped_count += 1
                    continue
                
                # Создаем индекс
                cursor.execute(f'''
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name}({column_name})
                ''')
                
                logger.info(f"Создан индекс: {index_name} на {table_name}.{column_name}")
                created_count += 1
                
            except sqlite3.Error as e:
                logger.error(f"Ошибка при создании индекса {index_name}: {e}")
                error_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info("=" * 60)
        logger.info(f"Итоги создания индексов:")
        logger.info(f"  Создано: {created_count}")
        logger.info(f"  Пропущено (уже существуют): {skipped_count}")
        logger.info(f"  Ошибок: {error_count}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Критическая ошибка при добавлении индексов: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Добавление индексов в базу данных")
    print("=" * 60)
    
    # Определяем путь к БД
    db_path = os.environ.get('DATABASE_PATH', 'database/service_center.db')
    
    if add_indexes(db_path):
        print("\n✓ Индексы успешно добавлены!")
    else:
        print("\n✗ Ошибка при добавлении индексов")
        exit(1)

