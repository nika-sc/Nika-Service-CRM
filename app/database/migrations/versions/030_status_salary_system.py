"""
Миграция 030: Система статусов и зарплаты.

Добавляет:
- Расширение order_statuses (группы, флаги, архив)
- Расширение managers и masters (настройки зарплаты)
- Расширение services и parts (настройки зарплаты)
- Таблица salary_accruals (начисления зарплаты)
- Таблица order_status_history (если еще нет)
- Таблица system_settings (настройки системы, НДС)
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table: str, column: str) -> bool:
    """Проверяет существование колонки в таблице."""
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    return column in cols


def _table_exists(cursor, table: str) -> bool:
    """Проверяет существование таблицы."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 030_status_salary_system: система статусов и зарплаты")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Расширение order_statuses
        logger.info("Расширение таблицы order_statuses...")
        for col, ddl in [
            ("group_name", "ALTER TABLE order_statuses ADD COLUMN group_name TEXT"),
            ("triggers_payment_modal", "ALTER TABLE order_statuses ADD COLUMN triggers_payment_modal INTEGER DEFAULT 0"),
            ("accrues_salary", "ALTER TABLE order_statuses ADD COLUMN accrues_salary INTEGER DEFAULT 0"),
            ("is_archived", "ALTER TABLE order_statuses ADD COLUMN is_archived INTEGER DEFAULT 0"),
            ("is_final", "ALTER TABLE order_statuses ADD COLUMN is_final INTEGER DEFAULT 0"),
            ("blocks_edit", "ALTER TABLE order_statuses ADD COLUMN blocks_edit INTEGER DEFAULT 0"),
            ("requires_warranty", "ALTER TABLE order_statuses ADD COLUMN requires_warranty INTEGER DEFAULT 0"),
            ("requires_comment", "ALTER TABLE order_statuses ADD COLUMN requires_comment INTEGER DEFAULT 0"),
            ("client_name", "ALTER TABLE order_statuses ADD COLUMN client_name TEXT"),
            ("client_description", "ALTER TABLE order_statuses ADD COLUMN client_description TEXT"),
        ]:
            if not _column_exists(cursor, "order_statuses", col):
                cursor.execute(ddl)
                logger.info(f"Добавлена колонка order_statuses.{col}")
        
        # 2. Расширение managers
        logger.info("Расширение таблицы managers...")
        for col, ddl in [
            ("salary_rule_type", "ALTER TABLE managers ADD COLUMN salary_rule_type TEXT"),
            ("salary_rule_value", "ALTER TABLE managers ADD COLUMN salary_rule_value REAL"),
            ("active", "ALTER TABLE managers ADD COLUMN active INTEGER DEFAULT 1"),
            ("comment", "ALTER TABLE managers ADD COLUMN comment TEXT"),
            ("updated_at", "ALTER TABLE managers ADD COLUMN updated_at TIMESTAMP"),
        ]:
            if not _column_exists(cursor, "managers", col):
                cursor.execute(ddl)
                logger.info(f"Добавлена колонка managers.{col}")
        
        # 3. Расширение masters
        logger.info("Расширение таблицы masters...")
        for col, ddl in [
            ("salary_rule_type", "ALTER TABLE masters ADD COLUMN salary_rule_type TEXT"),
            ("salary_rule_value", "ALTER TABLE masters ADD COLUMN salary_rule_value REAL"),
            ("active", "ALTER TABLE masters ADD COLUMN active INTEGER DEFAULT 1"),
            ("comment", "ALTER TABLE masters ADD COLUMN comment TEXT"),
            ("updated_at", "ALTER TABLE masters ADD COLUMN updated_at TIMESTAMP"),
        ]:
            if not _column_exists(cursor, "masters", col):
                cursor.execute(ddl)
                logger.info(f"Добавлена колонка masters.{col}")
        
        # 4. Расширение services
        logger.info("Расширение таблицы services...")
        for col, ddl in [
            ("salary_rule_type", "ALTER TABLE services ADD COLUMN salary_rule_type TEXT"),
            ("salary_rule_value", "ALTER TABLE services ADD COLUMN salary_rule_value REAL"),
        ]:
            if not _column_exists(cursor, "services", col):
                cursor.execute(ddl)
                logger.info(f"Добавлена колонка services.{col}")
        
        # 5. Расширение parts
        logger.info("Расширение таблицы parts...")
        for col, ddl in [
            ("salary_rule_type", "ALTER TABLE parts ADD COLUMN salary_rule_type TEXT"),
            ("salary_rule_value", "ALTER TABLE parts ADD COLUMN salary_rule_value REAL"),
        ]:
            if not _column_exists(cursor, "parts", col):
                cursor.execute(ddl)
                logger.info(f"Добавлена колонка parts.{col}")
        
        # 6. Таблица salary_accruals
        logger.info("Создание таблицы salary_accruals...")
        if not _table_exists(cursor, "salary_accruals"):
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS salary_accruals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    base_amount_cents INTEGER NOT NULL,
                    profit_cents INTEGER NOT NULL,
                    rule_type TEXT NOT NULL,
                    rule_value REAL NOT NULL,
                    calculated_from TEXT NOT NULL,
                    calculated_from_id INTEGER,
                    vat_included INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_accruals_order_id ON salary_accruals(order_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_accruals_user_id ON salary_accruals(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_accruals_role ON salary_accruals(role)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_salary_accruals_created_at ON salary_accruals(created_at)')
            logger.info("Таблица salary_accruals создана")
        
        # 7. Таблица order_status_history (если еще нет)
        logger.info("Проверка таблицы order_status_history...")
        if not _table_exists(cursor, "order_status_history"):
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    status_id INTEGER NOT NULL,
                    user_id INTEGER,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (status_id) REFERENCES order_statuses(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_status_history_order_id ON order_status_history(order_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_status_history_status_id ON order_status_history(status_id)')
            logger.info("Таблица order_status_history создана")
        
        # 8. Таблица system_settings
        logger.info("Создание таблицы system_settings...")
        if not _table_exists(cursor, "system_settings"):
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key)')
            logger.info("Таблица system_settings создана")
            
            # Заполняем дефолтные настройки
            cursor.execute('''
                INSERT OR IGNORE INTO system_settings (key, value, description) VALUES
                    ('vat_enabled', '0', 'Учитывать НДС в расчете зарплаты (1 = да, 0 = нет)'),
                    ('vat_rate', '20', 'Ставка НДС в процентах (по умолчанию 20%)')
            ''')
            logger.info("Дефолтные настройки системы добавлены")
        
        # 9. Обновление существующих статусов (установка групп по умолчанию)
        logger.info("Обновление существующих статусов...")
        cursor.execute('''
            UPDATE order_statuses 
            SET group_name = CASE 
                WHEN code IN ('new', 'created') THEN 'Новые'
                WHEN code IN ('in_progress', 'working', 'repairing') THEN 'В работе'
                WHEN code IN ('pending', 'deferred', 'postponed') THEN 'Отложенные'
                WHEN code IN ('ready', 'completed', 'done', 'finished') THEN 'Готовые'
                WHEN code IN ('closed', 'issued', 'completed_success') THEN 'Закрытые успешно'
                WHEN code IN ('cancelled', 'rejected', 'completed_fail') THEN 'Закрытые неуспешно'
                ELSE 'Новые'
            END
            WHERE group_name IS NULL
        ''')
        
        # Устанавливаем is_final для закрытых статусов
        cursor.execute('''
            UPDATE order_statuses 
            SET is_final = 1, accrues_salary = 1, triggers_payment_modal = 1
            WHERE code IN ('closed', 'issued', 'completed', 'done', 'finished', 'completed_success')
        ''')
        
        logger.info("Существующие статусы обновлены")
        
        # Устанавливаем updated_at для существующих записей
        cursor.execute('UPDATE managers SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL')
        cursor.execute('UPDATE masters SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL')
        
        conn.commit()
        logger.info("Миграция 030_status_salary_system успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 030_status_salary_system: SQLite не поддерживает DROP COLUMN без пересоздания таблиц")
    logger.warning("Для полного отката потребуется пересоздание таблиц")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем новые таблицы
        if _table_exists(cursor, "salary_accruals"):
            cursor.execute("DROP TABLE IF EXISTS salary_accruals")
            logger.info("Таблица salary_accruals удалена")
        
        if _table_exists(cursor, "system_settings"):
            cursor.execute("DROP TABLE IF EXISTS system_settings")
            logger.info("Таблица system_settings удалена")
        
        # order_status_history не удаляем, так как она может использоваться
        
        conn.commit()
        logger.info("Миграция 030_status_salary_system частично откачена (колонки остались)")

