"""
Миграция 055: база расчёта зарплаты менеджера (прибыль/выручка) и правила по умолчанию.

- Добавляет в managers колонку salary_rule_base: 'profit' (по умолчанию) или 'revenue'.
  При 'revenue' зарплата менеджера считается от выручки заказа, при 'profit' — от прибыли.
- Задаёт правила зарплаты по именам:
  Мастера: Андрей 50% с прибыли, Сергей 60%, Сергей 01 50%, остальные 50%.
  Менеджер Ника Сервис: 3% с выручки всего заказа (salary_rule_base='revenue').
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return column in [row[1] for row in cursor.fetchall()]


def up():
    logger.info("Применение миграции 055: salary_rule_base и правила по умолчанию")
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if not _column_exists(cursor, "managers", "salary_rule_base"):
            cursor.execute(
                "ALTER TABLE managers ADD COLUMN salary_rule_base TEXT DEFAULT 'profit'"
            )
            logger.info("Добавлена колонка managers.salary_rule_base")
        else:
            logger.info("Колонка managers.salary_rule_base уже существует")

        # Мастера: по именам (процент с прибыли)
        for name, pct in [("Сергей", 60), ("Андрей", 50), ("Сергей 01", 50)]:
            cursor.execute(
                "UPDATE masters SET salary_rule_type = 'percent', salary_rule_value = ? WHERE TRIM(name) = ?",
                (pct, name),
            )
            if cursor.rowcount:
                logger.info(f"Мастер '{name}': {pct}%% с прибыли")

        # Остальные мастера: 50% с прибыли (у кого правило ещё не задано)
        cursor.execute(
            """
            UPDATE masters
            SET salary_rule_type = 'percent', salary_rule_value = 50
            WHERE salary_rule_type IS NULL OR salary_rule_value IS NULL
            """
        )
        if cursor.rowcount:
            logger.info(f"Остальные мастера: 50%% с прибыли (обновлено {cursor.rowcount})")

        # Менеджер Ника Сервис: 3% с выручки заказа
        cursor.execute(
            """
            UPDATE managers
            SET salary_rule_type = 'percent', salary_rule_value = 3, salary_rule_base = 'revenue'
            WHERE TRIM(name) = 'Ника Сервис'
            """
        )
        if cursor.rowcount:
            logger.info("Менеджер 'Ника Сервис': 3%% с выручки заказа")
        conn.commit()
    logger.info("Миграция 055 успешно применена")


def down():
    logger.info("Откат миграции 055")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if _column_exists(cursor, "managers", "salary_rule_base"):
            # SQLite не поддерживает DROP COLUMN в старых версиях — колонку оставляем
            cursor.execute("UPDATE managers SET salary_rule_base = 'profit' WHERE 1=1")
            conn.commit()
            logger.info("Поле salary_rule_base сброшено на 'profit'")
    logger.info("Откат миграции 055 завершён")
