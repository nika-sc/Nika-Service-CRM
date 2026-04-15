"""
Миграция 026: Поддержка разовых услуг и товаров в заявках.

Зачем:
- Добавить возможность создавать разовые услуги/товары в заявках без привязки к справочнику
- Для разовых услуг/товаров service_id/part_id может быть NULL, но обязательно должно быть поле name

Изменения:
1. Добавить поле `name` в таблицы `order_services` и `order_parts`
2. Сделать `service_id` и `part_id` опциональными (NULL)
3. Удалить UNIQUE constraint на (order_id, service_id) и (order_id, part_id)
4. Добавить CHECK constraint: либо service_id/part_id должен быть указан, либо name
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 026_one_time_services_parts: поддержка разовых услуг и товаров")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Обновляем таблицу order_services
        logger.info("Обновление таблицы order_services...")
        
        # Проверяем, существует ли поле name
        cursor.execute("PRAGMA table_info(order_services)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'name' not in columns:
            # Добавляем поле name
            cursor.execute("ALTER TABLE order_services ADD COLUMN name TEXT")
            logger.info("Добавлено поле name в order_services")
        
        # Делаем service_id опциональным (удаляем NOT NULL)
        # SQLite не поддерживает ALTER COLUMN, поэтому нужно пересоздать таблицу
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_services_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                service_id INTEGER,
                name TEXT,
                quantity INTEGER DEFAULT 1,
                price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id),
                CHECK ((service_id IS NOT NULL) OR (name IS NOT NULL AND name != ''))
            )
        """)
        
        # Копируем данные
        cursor.execute("""
            INSERT INTO order_services_new (id, order_id, service_id, name, quantity, price, created_at)
            SELECT id, order_id, service_id, NULL, quantity, price, created_at
            FROM order_services
        """)
        
        # Удаляем старую таблицу и переименовываем новую
        cursor.execute("DROP TABLE order_services")
        cursor.execute("ALTER TABLE order_services_new RENAME TO order_services")
        
        # Восстанавливаем индексы
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_services_order_id ON order_services(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_services_service_id ON order_services(service_id)")
        
        logger.info("Таблица order_services обновлена")

        # 2. Обновляем таблицу order_parts
        logger.info("Обновление таблицы order_parts...")
        
        # Проверяем, существует ли поле name
        cursor.execute("PRAGMA table_info(order_parts)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'name' not in columns:
            # Добавляем поле name
            cursor.execute("ALTER TABLE order_parts ADD COLUMN name TEXT")
            logger.info("Добавлено поле name в order_parts")
        
        # Делаем part_id опциональным (удаляем NOT NULL)
        # SQLite не поддерживает ALTER COLUMN, поэтому нужно пересоздать таблицу
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_parts_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                part_id INTEGER,
                name TEXT,
                quantity INTEGER NOT NULL DEFAULT 1,
                price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                purchase_price DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES parts(id),
                CHECK ((part_id IS NOT NULL) OR (name IS NOT NULL AND name != ''))
            )
        """)
        
        # Копируем данные
        cursor.execute("""
            INSERT INTO order_parts_new (id, order_id, part_id, name, quantity, price, purchase_price, created_at)
            SELECT id, order_id, part_id, NULL, quantity, price, purchase_price, created_at
            FROM order_parts
        """)
        
        # Удаляем старую таблицу и переименовываем новую
        cursor.execute("DROP TABLE order_parts")
        cursor.execute("ALTER TABLE order_parts_new RENAME TO order_parts")
        
        # Восстанавливаем индексы
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_parts_order_id ON order_parts(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_parts_part_id ON order_parts(part_id)")
        
        logger.info("Таблица order_parts обновлена")

        conn.commit()
        logger.info("Миграция 026_one_time_services_parts успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 026_one_time_services_parts: удаление поддержки разовых услуг и товаров")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Удаляем записи с NULL service_id/part_id (разовые услуги/товары)
        cursor.execute("DELETE FROM order_services WHERE service_id IS NULL")
        cursor.execute("DELETE FROM order_parts WHERE part_id IS NULL")

        # Восстанавливаем order_services
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_services_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                price DECIMAL(10, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id),
                UNIQUE(order_id, service_id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO order_services_old (id, order_id, service_id, quantity, price, created_at)
            SELECT id, order_id, service_id, quantity, price, created_at
            FROM order_services
            WHERE service_id IS NOT NULL
        """)
        
        cursor.execute("DROP TABLE order_services")
        cursor.execute("ALTER TABLE order_services_old RENAME TO order_services")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_services_order_id ON order_services(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_services_service_id ON order_services(service_id)")

        # Восстанавливаем order_parts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_parts_old (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                purchase_price DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES parts(id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO order_parts_old (id, order_id, part_id, quantity, price, purchase_price, created_at)
            SELECT id, order_id, part_id, quantity, price, purchase_price, created_at
            FROM order_parts
            WHERE part_id IS NOT NULL
        """)
        
        cursor.execute("DROP TABLE order_parts")
        cursor.execute("ALTER TABLE order_parts_old RENAME TO order_parts")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_parts_order_id ON order_parts(order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_parts_part_id ON order_parts(part_id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_order_parts_order_part ON order_parts(order_id, part_id)")

        conn.commit()
        logger.info("Миграция 026_one_time_services_parts откачена")

