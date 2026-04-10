"""
Миграция 031: Дополнительные индексы для производительности.

Добавляет индексы для оптимизации частых запросов:
- Индексы для отчетов (даты, фильтры)
- Составные индексы для JOIN операций
- Индексы для поиска и сортировки
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection) -> None:
    """Применить миграцию."""
    cursor = conn.cursor()
    
    # Индексы для cash_transactions (отчеты по финансам)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cash_transactions_date_type 
        ON cash_transactions(transaction_date, transaction_type)
    """)
    logger.info("Создан индекс idx_cash_transactions_date_type")
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_cash_transactions_category 
        ON cash_transactions(category_id)
    """)
    logger.info("Создан индекс idx_cash_transactions_category")
    
    # Индексы для shop_sales (отчеты по магазину)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_shop_sales_date 
        ON shop_sales(sale_date)
    """)
    logger.info("Создан индекс idx_shop_sales_date")
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_shop_sales_customer 
        ON shop_sales(customer_id)
    """)
    logger.info("Создан индекс idx_shop_sales_customer")
    
    # Индексы для stock_movements (складские отчеты)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_stock_movements_date_type 
        ON stock_movements(created_at, movement_type)
    """)
    logger.info("Создан индекс idx_stock_movements_date_type")
    
    # Индексы для order_parts (отчеты по заявкам)
    # Проверяем наличие колонки is_sold перед созданием индекса
    cursor.execute("PRAGMA table_info(order_parts)")
    order_parts_columns = [row[1] for row in cursor.fetchall()]
    if 'is_sold' in order_parts_columns:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_parts_sold 
            ON order_parts(order_id, is_sold)
        """)
        logger.info("Создан индекс idx_order_parts_sold")
    else:
        # Если колонки нет, создаем индекс только по order_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_parts_order_id_alt 
            ON order_parts(order_id)
        """)
        logger.info("Создан индекс idx_order_parts_order_id_alt (is_sold отсутствует)")
    
    # Индексы для order_services (отчеты по услугам)
    cursor.execute("PRAGMA table_info(order_services)")
    order_services_columns = [row[1] for row in cursor.fetchall()]
    if 'is_sold' in order_services_columns:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_services_sold 
            ON order_services(order_id, is_sold)
        """)
        logger.info("Создан индекс idx_order_services_sold")
    else:
        # Если колонки нет, создаем индекс только по order_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_order_services_order_id_alt 
            ON order_services(order_id)
        """)
        logger.info("Создан индекс idx_order_services_order_id_alt (is_sold отсутствует)")
    
    # Индексы для action_logs (логи действий)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_action_logs_entity 
        ON action_logs(entity_type, entity_id)
    """)
    logger.info("Создан индекс idx_action_logs_entity")
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_action_logs_created 
        ON action_logs(created_at)
    """)
    logger.info("Создан индекс idx_action_logs_created")
    
    # Индексы для salary_accruals (отчеты по зарплате)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_salary_accruals_order 
        ON salary_accruals(order_id)
    """)
    logger.info("Создан индекс idx_salary_accruals_order")
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_salary_accruals_user 
        ON salary_accruals(user_id, role)
    """)
    logger.info("Создан индекс idx_salary_accruals_user")
    
    conn.commit()
    logger.info("Миграция 031: индексы для производительности добавлены")


def down(conn: sqlite3.Connection) -> None:
    """Откатить миграцию."""
    cursor = conn.cursor()
    
    indexes = [
        "idx_cash_transactions_date_type",
        "idx_cash_transactions_category",
        "idx_shop_sales_date",
        "idx_shop_sales_customer",
        "idx_stock_movements_date_type",
        "idx_order_parts_sold",
        "idx_order_parts_order_id_alt",
        "idx_order_services_sold",
        "idx_order_services_order_id_alt",
        "idx_action_logs_entity",
        "idx_action_logs_created",
        "idx_salary_accruals_order",
        "idx_salary_accruals_user",
    ]
    
    for idx_name in indexes:
        cursor.execute(f"DROP INDEX IF EXISTS {idx_name}")
    
    conn.commit()
    logger.info("Миграция 031: индексы удалены")
