"""RBAC helpers shared across routes."""


def can_create_role(current_user_role: str, target_role: str) -> bool:
    """
    Проверяет, может ли текущий пользователь создать/назначить указанную роль.

    admin → admin | manager | master | viewer
    manager / manager_* → только master
    """
    current = (current_user_role or "viewer").strip()
    target = (target_role or "").strip().lower()
    if not target:
        return False

    if current == "admin":
        return target in ("admin", "manager", "master", "viewer")

    if current == "manager" or current.startswith("manager_"):
        return target == "master"

    return False


def can_assign_user_role(
    *,
    actor_role: str,
    target_role: str,
    target_user_id: int | None = None,
    actor_user_id: int | None = None,
) -> bool:
    """Проверка назначения роли с учётом самоповышения до admin."""
    if not can_create_role(actor_role, target_role):
        return False
    if (
        target_role == "admin"
        and actor_role != "admin"
        and target_user_id is not None
        and actor_user_id is not None
        and target_user_id == actor_user_id
    ):
        return False
    return True
