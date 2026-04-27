"""
Миграция 014: Починка целостности БД и несоответствий схемы.

Цели:
1) Восстановить целостность FK для orders -> devices (создать placeholder devices для "потерянных" device_id)
2) Привести order_comments к корректной схеме: order_id INTEGER -> FK на orders(id)
   - мигрировать данные из текущей таблицы (которая может иметь order_id как TEXT/UUID)
   - сохранить "непереносимые" строки в order_comments_orphan
3) Нормализовать роли пользователей: заменить role='editor' -> 'manager'
4) Сделать бэкап файла БД перед изменениями (если ещё не сделан в рамках этой миграции)

Примечание:
SQLite применяет PRAGMA foreign_keys per-connection. В приложении это включено в get_db_connection().
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime
import sqlite3

from app.database.connection import get_db_connection
from app.config import Config

logger = logging.getLogger(__name__)


def _backup_db_file() -> None:
    """Создаёт копию файла БД рядом с исходником (database/backups/...)."""
    try:
        db_path = os.environ.get("DATABASE_PATH", Config.DATABASE_PATH)
        if not db_path or not os.path.exists(db_path):
            logger.warning(f"Бэкап БД пропущен: файл не найден ({db_path})")
            return

        backup_dir = os.path.join(os.path.dirname(db_path) or ".", "backups")
        os.makedirs(backup_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"service_center.db.backup_{ts}")
        shutil.copy2(db_path, backup_path)
        logger.info(f"Создан бэкап БД: {backup_path}")
    except Exception as e:
        # Не падаем, но фиксируем
        logger.warning(f"Не удалось создать бэкап БД: {e}")


def up():
    logger.info("Применение миграции 014_fix_db_integrity")

    _backup_db_file()

    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cursor = conn.cursor()

        # 0) Нормализация ролей пользователей (editor -> manager)
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if cursor.fetchone():
                cursor.execute("UPDATE users SET role = 'manager' WHERE role = 'editor'")
                if cursor.rowcount:
                    logger.info(f"Обновлены роли пользователей editor -> manager: {cursor.rowcount}")
        except Exception as e:
            logger.warning(f"Не удалось нормализовать роли пользователей: {e}")

        # 1) Починка orders.device_id -> devices.id (создаём placeholder devices)
        try:
            cursor.execute("""
                SELECT DISTINCT o.device_id AS missing_device_id, o.customer_id AS customer_id
                FROM orders o
                LEFT JOIN devices d ON d.id = o.device_id
                WHERE o.device_id IS NOT NULL AND d.id IS NULL
            """)
            missing = cursor.fetchall()
            if missing:
                # Берём минимальные существующие type/brand, чтобы создать валидную запись
                cursor.execute("SELECT MIN(id) FROM device_types")
                device_type_id = cursor.fetchone()[0] or 1
                cursor.execute("SELECT MIN(id) FROM device_brands")
                device_brand_id = cursor.fetchone()[0] or 1

                created = 0
                for row in missing:
                    dev_id = int(row["missing_device_id"])
                    cust_id = int(row["customer_id"])
                    # Вставляем с фиксированным id, чтобы закрыть FK
                    cursor.execute("""
                        INSERT OR IGNORE INTO devices (
                            id, customer_id, device_type_id, device_brand_id, serial_number, created_at
                        ) VALUES (?, ?, ?, ?, NULL, CURRENT_TIMESTAMP)
                    """, (dev_id, cust_id, device_type_id, device_brand_id))
                    if cursor.rowcount:
                        created += 1

                logger.info(f"Создано placeholder devices для закрытия FK: {created}/{len(missing)}")
        except Exception as e:
            logger.error(f"Ошибка при починке orders.device_id -> devices.id: {e}", exc_info=True)
            raise

        # 2) Починка order_comments: приводим к order_id INTEGER -> FK orders(id)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_comments'")
        if cursor.fetchone():
            try:
                # Создаём таблицу для "осиротевших" комментариев (на всякий случай)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS order_comments_orphan (
                        id INTEGER PRIMARY KEY,
                        order_id_raw TEXT NOT NULL,
                        author_type TEXT,
                        author_id INTEGER,
                        author_name TEXT,
                        comment_text TEXT,
                        is_internal INTEGER,
                        created_at TIMESTAMP,
                        migrated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        reason TEXT
                    )
                """)

                # Временная новая таблица с правильным FK
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS order_comments_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        author_type TEXT NOT NULL DEFAULT 'manager',
                        author_id INTEGER,
                        author_name TEXT,
                        comment_text TEXT NOT NULL,
                        is_internal INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                    )
                """)

                # Индексы
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_comments_new_order_id ON order_comments_new(order_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_comments_new_created_at ON order_comments_new(created_at DESC)")

                # Читаем все старые комментарии, учитывая что часть колонок
                # могла отсутствовать в старой схеме.
                cursor.execute("PRAGMA table_info(order_comments)")
                existing_columns = {row[1] for row in cursor.fetchall()}

                def _sel(column_name: str, fallback_sql: str):
                    return column_name if column_name in existing_columns else fallback_sql

                cursor.execute(f"""
                    SELECT
                        id,
                        order_id,
                        {_sel("author_type", "'manager'")} AS author_type,
                        {_sel("author_id", "NULL")} AS author_id,
                        {_sel("author_name", "NULL")} AS author_name,
                        comment_text,
                        COALESCE({_sel("is_internal", "0")}, 0) AS is_internal,
                        {_sel("created_at", "CURRENT_TIMESTAMP")} AS created_at
                    FROM order_comments
                    ORDER BY id
                """)
                rows = cursor.fetchall()

                migrated = 0
                orphaned = 0

                for r in rows:
                    raw = r["order_id"]
                    raw_str = str(raw) if raw is not None else ""
                    order_id_int = None

                    # 1) Если похоже на int (старый ожидаемый формат)
                    try:
                        if raw_str.isdigit():
                            order_id_int = int(raw_str)
                    except Exception:
                        order_id_int = None

                    # 2) Если похоже на UUID, маппим по orders.order_id (uuid)
                    if order_id_int is None and raw_str and "-" in raw_str:
                        cursor.execute("SELECT id FROM orders WHERE order_id = ? LIMIT 1", (raw_str,))
                        o = cursor.fetchone()
                        if o:
                            order_id_int = int(o[0])

                    # 3) Проверяем, что такая заявка реально существует
                    if order_id_int is not None:
                        cursor.execute("SELECT 1 FROM orders WHERE id = ? LIMIT 1", (order_id_int,))
                        if not cursor.fetchone():
                            order_id_int = None

                    if order_id_int is None:
                        cursor.execute("""
                            INSERT OR REPLACE INTO order_comments_orphan
                            (id, order_id_raw, author_type, author_id, author_name, comment_text, is_internal, created_at, reason)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            r["id"],
                            raw_str,
                            r["author_type"],
                            r["author_id"],
                            r["author_name"],
                            r["comment_text"],
                            r["is_internal"],
                            r["created_at"],
                            "cannot_map_order_id",
                        ))
                        orphaned += 1
                        continue

                    cursor.execute("""
                        INSERT OR REPLACE INTO order_comments_new
                        (id, order_id, author_type, author_id, author_name, comment_text, is_internal, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r["id"],
                        order_id_int,
                        r["author_type"],
                        r["author_id"],
                        r["author_name"],
                        r["comment_text"],
                        r["is_internal"],
                        r["created_at"],
                    ))
                    migrated += 1

                # Переименовываем таблицы: сохраняем старую как backup
                cursor.execute("ALTER TABLE order_comments RENAME TO order_comments_old_014")
                cursor.execute("ALTER TABLE order_comments_new RENAME TO order_comments")

                # Пересоздаём индексы на новой таблице под ожидаемые имена
                cursor.execute("DROP INDEX IF EXISTS idx_order_comments_order_id")
                cursor.execute("DROP INDEX IF EXISTS idx_order_comments_created_at")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_comments_order_id ON order_comments(order_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_comments_created_at ON order_comments(created_at DESC)")

                logger.info(f"order_comments мигрировано: ok={migrated}, orphan={orphaned}")
            except Exception as e:
                logger.error(f"Ошибка при миграции order_comments: {e}", exc_info=True)
                raise

        conn.commit()
        logger.info("Миграция 014_fix_db_integrity успешно применена")


def down():
    """
    Откат миграции возможен частично:
    - роли users manager->editor не откатываем (небезопасно/неоднозначно)
    - placeholder devices не удаляем
    - order_comments: если есть order_comments_old_014 — вернём её как order_comments
    """
    logger.warning("Откат миграции 014_fix_db_integrity (частичный)")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_comments_old_014'")
        if cursor.fetchone():
            try:
                cursor.execute("ALTER TABLE order_comments RENAME TO order_comments_new_014")
                cursor.execute("ALTER TABLE order_comments_old_014 RENAME TO order_comments")
                cursor.execute("DROP INDEX IF EXISTS idx_order_comments_new_order_id")
                cursor.execute("DROP INDEX IF EXISTS idx_order_comments_new_created_at")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_comments_order_id ON order_comments(order_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_order_comments_created_at ON order_comments(created_at DESC)")
                logger.info("order_comments восстановлена из order_comments_old_014")
            except Exception as e:
                logger.error(f"Не удалось откатить order_comments: {e}", exc_info=True)
                raise

        conn.commit()
        logger.info("Миграция 014_fix_db_integrity откачена (частично)")


