"""
Миграция 035: Дополнительные права для модулей (финансы/магазин/логи/статусы).

Добавляет новые permissions:
  - view_finance, manage_finance
  - view_shop, manage_shop
  - view_action_logs
  - manage_statuses

И назначает их стандартным ролям:
  - admin: все новые права
  - manager: view_finance, manage_finance, view_shop, manage_shop, manage_statuses
  - master/viewer: без изменений
"""

from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    logger.info("Применение миграции 035_rbac_module_permissions")

    new_permissions = [
        ("view_finance", "Просмотр финансового модуля"),
        ("manage_finance", "Управление финансовым модулем"),
        ("view_shop", "Просмотр модуля Магазин"),
        ("manage_shop", "Управление модулем Магазин"),
        ("view_action_logs", "Просмотр логов действий"),
        ("manage_statuses", "Управление статусами заявок"),
    ]

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1) Создаем permissions (если еще не существуют)
        for name, desc in new_permissions:
            cursor.execute(
                "INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)",
                (name, desc),
            )

        # 2) Получаем id новых прав
        cursor.execute(
            "SELECT id, name FROM permissions WHERE name IN ({})".format(
                ",".join(["?"] * len(new_permissions))
            ),
            [p[0] for p in new_permissions],
        )
        perm_ids = {name: pid for pid, name in cursor.fetchall()}

        # 3) Назначаем ролям
        role_map = {
            "admin": [
                "view_finance",
                "manage_finance",
                "view_shop",
                "manage_shop",
                "view_action_logs",
                "manage_statuses",
            ],
            "manager": [
                "view_finance",
                "manage_finance",
                "view_shop",
                "manage_shop",
                "manage_statuses",
            ],
        }

        for role, perm_names in role_map.items():
            for perm_name in perm_names:
                pid = perm_ids.get(perm_name)
                if not pid:
                    continue
                cursor.execute(
                    "INSERT OR IGNORE INTO role_permissions (role, permission_id) VALUES (?, ?)",
                    (role, pid),
                )

        conn.commit()
        logger.info("Миграция 035_rbac_module_permissions успешно применена")


def down():
    logger.warning("Откат миграции 035_rbac_module_permissions")

    perm_names = [
        "view_finance",
        "manage_finance",
        "view_shop",
        "manage_shop",
        "view_action_logs",
        "manage_statuses",
    ]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Удаляем связи role_permissions для этих permissions
        cursor.execute(
            "DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE name IN ({}))".format(
                ",".join(["?"] * len(perm_names))
            ),
            perm_names,
        )
        # Удаляем сами permissions
        cursor.execute(
            "DELETE FROM permissions WHERE name IN ({})".format(
                ",".join(["?"] * len(perm_names))
            ),
            perm_names,
        )
        conn.commit()
        logger.info("Миграция 035_rbac_module_permissions откачена")

