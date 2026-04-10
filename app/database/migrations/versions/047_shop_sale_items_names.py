"""
Миграция 047: Заполнение service_name и part_name в shop_sale_items.

Обновляет существующие позиции чеков, у которых отсутствуют наименования,
подставляя их из таблиц services и parts по service_id / part_id.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 047_shop_sale_items_names")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Обновить service_name из services для позиций с service_id
        cursor.execute('''
            UPDATE shop_sale_items
            SET service_name = (
                SELECT s.name FROM services s WHERE s.id = shop_sale_items.service_id
            )
            WHERE service_id IS NOT NULL
              AND (service_name IS NULL OR TRIM(COALESCE(service_name, '')) = '')
        ''')
        services_updated = cursor.rowcount

        # Обновить part_name из parts для позиций с part_id
        cursor.execute('''
            UPDATE shop_sale_items
            SET part_name = (
                SELECT p.name FROM parts p WHERE p.id = shop_sale_items.part_id
            )
            WHERE part_id IS NOT NULL
              AND (part_name IS NULL OR TRIM(COALESCE(part_name, '')) = '')
        ''')
        parts_updated = cursor.rowcount

        conn.commit()
        logger.info(
            "Миграция 047: обновлено service_name: %d, part_name: %d",
            services_updated, parts_updated
        )


def down():
    """Откат миграции — данные не откатываем, т.к. это data migration."""
    logger.info("Миграция 047: откат не требуется (data migration)")
