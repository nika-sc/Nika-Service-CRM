"""
Миграция 015: Очистка артефактов миграции 014.

После успешной миграции order_comments в 014 мы оставляли таблицу order_comments_old_014
для потенциального rollback. Но она содержит битые FK и ломает PRAGMA foreign_key_check.

В этой миграции:
- удаляем order_comments_old_014 (бэкап уже создан как файл в database/backups/).
"""

import logging
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 015_cleanup_014_artifacts")
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_comments_old_014'")
        if cur.fetchone():
            cur.execute("DROP TABLE IF EXISTS order_comments_old_014")
            logger.info("Удалена таблица order_comments_old_014")
        conn.commit()


def down():
    # Не восстанавливаем удалённую таблицу; бэкап лежит в файле БД.
    logger.warning("Откат миграции 015_cleanup_014_artifacts не выполняется (noop)")


