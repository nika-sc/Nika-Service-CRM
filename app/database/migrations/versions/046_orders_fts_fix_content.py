"""
Миграция 046: Исправление orders_fts — убрать content='orders'.

Таблица orders не содержит client_name, phone, email (они в customers).
При content='orders' SQLite ожидает в orders те же колонки, что в FTS,
поэтому при UPDATE orders срабатывала ошибка "no such column: T.client_name".

Пересоздаём orders_fts как standalone FTS (без content=), данные заполняются
триггерами из JOIN orders + customers + devices.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _table_exists(cursor, table_name: str) -> bool:
    """Проверяет существование таблицы."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 046_orders_fts_fix_content")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Удаляем триггеры, чтобы не срабатывали при пересоздании таблицы
        for trigger in ('orders_fts_insert', 'orders_fts_update', 'orders_fts_delete'):
            cursor.execute(f'DROP TRIGGER IF EXISTS {trigger}')
        logger.info("Триггеры orders_fts удалены")

        # Удаляем старую FTS-таблицу (с content='orders')
        if _table_exists(cursor, 'orders_fts'):
            cursor.execute('DROP TABLE IF EXISTS orders_fts')
            logger.info("Таблица orders_fts удалена")

        # Создаём orders_fts без content= (standalone), чтобы данные шли только из триггеров
        cursor.execute('''
            CREATE VIRTUAL TABLE orders_fts USING fts5(
                order_id,
                client_name,
                phone,
                email,
                serial_number,
                device_type,
                device_brand,
                comment,
                symptom_tags,
                appearance
            )
        ''')
        logger.info("Таблица orders_fts создана (standalone)")

        # Заполняем из JOIN (как в 043)
        cursor.execute('''
            INSERT INTO orders_fts(rowid, order_id, client_name, phone, email, serial_number, device_type, device_brand, comment, symptom_tags, appearance)
            SELECT
                o.id,
                o.order_id,
                COALESCE(c.name, ''),
                COALESCE(c.phone, ''),
                COALESCE(c.email, ''),
                COALESCE(d.serial_number, ''),
                COALESCE(dt.name, ''),
                COALESCE(db.name, ''),
                COALESCE(o.comment, ''),
                COALESCE(o.symptom_tags, ''),
                COALESCE(o.appearance, '')
            FROM orders o
            LEFT JOIN customers c ON c.id = o.customer_id
            LEFT JOIN devices d ON d.id = o.device_id
            LEFT JOIN device_types dt ON dt.id = d.device_type_id
            LEFT JOIN device_brands db ON db.id = d.device_brand_id
        ''')
        logger.info("orders_fts заполнена из JOIN")

        # В FTS5 с content='' вставка по rowid может отличаться; проверяем синтаксис триггеров.
        # Триггер INSERT: после INSERT в orders добавляем строку в orders_fts
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS orders_fts_insert AFTER INSERT ON orders BEGIN
                INSERT INTO orders_fts(rowid, order_id, client_name, phone, email, serial_number, device_type, device_brand, comment, symptom_tags, appearance)
                SELECT
                    o.id,
                    o.order_id,
                    COALESCE(c.name, ''),
                    COALESCE(c.phone, ''),
                    COALESCE(c.email, ''),
                    COALESCE(d.serial_number, ''),
                    COALESCE(dt.name, ''),
                    COALESCE(db.name, ''),
                    COALESCE(o.comment, ''),
                    COALESCE(o.symptom_tags, ''),
                    COALESCE(o.appearance, '')
                FROM orders o
                LEFT JOIN customers c ON c.id = o.customer_id
                LEFT JOIN devices d ON d.id = o.device_id
                LEFT JOIN device_types dt ON dt.id = d.device_type_id
                LEFT JOIN device_brands db ON db.id = d.device_brand_id
                WHERE o.id = NEW.id;
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS orders_fts_update AFTER UPDATE ON orders BEGIN
                DELETE FROM orders_fts WHERE rowid = NEW.id;
                INSERT INTO orders_fts(rowid, order_id, client_name, phone, email, serial_number, device_type, device_brand, comment, symptom_tags, appearance)
                SELECT
                    o.id,
                    o.order_id,
                    COALESCE(c.name, ''),
                    COALESCE(c.phone, ''),
                    COALESCE(c.email, ''),
                    COALESCE(d.serial_number, ''),
                    COALESCE(dt.name, ''),
                    COALESCE(db.name, ''),
                    COALESCE(o.comment, ''),
                    COALESCE(o.symptom_tags, ''),
                    COALESCE(o.appearance, '')
                FROM orders o
                LEFT JOIN customers c ON c.id = o.customer_id
                LEFT JOIN devices d ON d.id = o.device_id
                LEFT JOIN device_types dt ON dt.id = d.device_type_id
                LEFT JOIN device_brands db ON db.id = d.device_brand_id
                WHERE o.id = NEW.id;
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS orders_fts_delete AFTER DELETE ON orders BEGIN
                DELETE FROM orders_fts WHERE rowid = OLD.id;
            END
        ''')

        logger.info("Триггеры orders_fts созданы заново")
        conn.commit()
    logger.info("Миграция 046_orders_fts_fix_content применена успешно")


def down():
    """Откат: возвращаем вариант с content='orders' (как в 043)."""
    logger.warning("Откат миграции 046 — пересоздание orders_fts с content='orders' не выполняется (приведёт к ошибке T.client_name). Оставлена standalone таблица.")
    # Не восстанавливаем старую схему, т.к. она нерабочая.
    pass
