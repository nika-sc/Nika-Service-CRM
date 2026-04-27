"""
Миграция 056: Синхронизация прав по умолчанию для стандартных ролей.

Добавляет недостающие связи role_permissions для ролей admin, manager, master, viewer,
чтобы доступ к модулям (в т.ч. Зарплата, Финансы) работал стабильно.
Не удаляет существующие права — только INSERT OR IGNORE.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 056_sync_default_role_permissions")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Получаем id всех прав по имени
        cursor.execute("SELECT id, name FROM permissions")
        perm_by_name = {row[1]: row[0] for row in cursor.fetchall()}

        # Матрица: роль -> список имён прав (добавляем только недостающие)
        default_role_permissions = {
            "admin": [
                "view_orders", "create_orders", "edit_orders", "delete_orders",
                "view_customers", "create_customers", "edit_customers", "delete_customers",
                "view_warehouse", "manage_warehouse", "view_reports", "manage_settings",
                "manage_users", "view_finance", "manage_finance", "view_shop", "manage_shop",
                "view_action_logs", "manage_statuses", "salary.view",
            ],
            "manager": [
                "view_orders", "create_orders", "edit_orders", "view_customers",
                "create_customers", "edit_customers", "view_warehouse", "manage_warehouse",
                "view_reports", "view_finance", "manage_finance", "view_shop", "manage_shop",
                "manage_statuses", "view_action_logs", "salary.view",
            ],
            "master": [
                "view_orders", "create_orders", "edit_orders", "view_customers",
                "view_warehouse", "salary.view",
            ],
            "viewer": [
                "view_orders", "view_customers",
            ],
        }

        added = 0
        for role, perm_names in default_role_permissions.items():
            for perm_name in perm_names:
                pid = perm_by_name.get(perm_name)
                if not pid:
                    logger.warning("Право %s не найдено в permissions, пропуск", perm_name)
                    continue
                cursor.execute(
                    "INSERT OR IGNORE INTO role_permissions (role, permission_id) VALUES (?, ?)",
                    (role, pid),
                )
                if cursor.rowcount > 0:
                    added += 1

        conn.commit()
        logger.info("Миграция 056_sync_default_role_permissions применена, добавлено связей: %s", added)


def down():
    logger.warning("Откат миграции 056 не удаляет данные — только добавленные связи можно снять вручную при необходимости")
    # Не удаляем role_permissions, чтобы не сломать кастомные роли
    pass
