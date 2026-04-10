"""
Миграция 016: Нормализация категории товара (parts.category_id).

Добавляет:
- parts.category_id INTEGER (id категории из part_categories)
- индекс по category_id

Мигрирует данные:
- для каждой parts.category (TEXT) ищем/создаём запись в part_categories
- заполняем parts.category_id соответствующим id

Старое поле parts.category (TEXT) сохраняем для обратной совместимости.
"""

import logging
import sqlite3
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 016_parts_category_id")
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cur = conn.cursor()

        # 1) Добавляем колонку category_id, если её нет
        cur.execute("PRAGMA table_info(parts)")
        cols = [r[1] for r in cur.fetchall()]
        if "category_id" not in cols:
            cur.execute("ALTER TABLE parts ADD COLUMN category_id INTEGER")
            logger.info("Добавлена колонка parts.category_id")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_parts_category_id ON parts(category_id)")

        # 2) Миграция существующих категорий
        cur.execute("""
            SELECT DISTINCT category
            FROM parts
            WHERE category IS NOT NULL AND TRIM(category) != ''
        """)
        categories = [r[0] for r in cur.fetchall()]

        for cat_name in categories:
            cur.execute("INSERT OR IGNORE INTO part_categories (name) VALUES (?)", (cat_name,))

        # 3) Заполняем category_id по имени категории
        cur.execute("""
            UPDATE parts
            SET category_id = (
                SELECT pc.id FROM part_categories pc WHERE pc.name = parts.category LIMIT 1
            )
            WHERE (category_id IS NULL OR category_id = 0)
              AND category IS NOT NULL AND TRIM(category) != ''
        """)

        conn.commit()
        logger.info("Миграция 016_parts_category_id успешно применена")


def down():
    # SQLite не поддерживает DROP COLUMN — откат только логический.
    logger.warning("Откат миграции 016_parts_category_id не поддерживается (SQLite DROP COLUMN отсутствует)")


