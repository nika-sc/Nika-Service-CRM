"""
Скрипт для очистки тестовых пользователей из таблицы users.

Логика:
- Показывает текущий список пользователей (id, username, role, is_active).
- Удаляет пользователей, которые выглядят как тестовые:
  - username содержит подстроку 'test', 'demo' или 'play' (без учёта регистра), ИЛИ
  - роль = 'viewer' и is_active = 0.
- Пользователя 'admin' и любых активных админов/менеджеров/мастеров не трогаем.

Запуск:
    python scripts/cleanup_test_users.py --dry-run   # только посмотреть, кого бы удалили
    python scripts/cleanup_test_users.py             # реально удалить
"""
import argparse
import sqlite3
from app.database.connection import get_db_connection


def list_users():
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, role, is_active FROM users ORDER BY id")
        return list(cur.fetchall())


def is_test_like(username: str) -> bool:
    u = (username or "").lower()
    return any(key in u for key in ("test", "demo", "play", "e2e", "qa"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Только показать, кого удалим")
    parser.add_argument("--yes", action="store_true", help="Удалять без дополнительного подтверждения")
    args = parser.parse_args()

    users = list_users()
    print("Текущие пользователи (id, username, role, is_active):")
    for u in users:
        print(f"{u['id']:3}  {u['username']:<30}  {u['role']:<10}  {u['is_active']}")

    to_delete_ids = []
    for u in users:
        uid = u["id"]
        username = u["username"]
        role = u["role"]
        is_active = u["is_active"]

        # Никогда не удаляем админа явно
        if username == "admin" or role == "admin":
            continue

        # Эвристика: тестовые
        if is_test_like(username):
            to_delete_ids.append(uid)
            continue

        # Неактивные viewer'ы — скорее всего мусор от тестов
        if role == "viewer" and not is_active:
            to_delete_ids.append(uid)

    if not to_delete_ids:
        print("\nНет кандидатов на удаление по текущим правилам.")
        return

    print("\nКандидаты на удаление (id):", ", ".join(map(str, to_delete_ids)))

    if args.dry_run:
        print("DRY-RUN режим: удаление НЕ выполняется.")
        return

    if not args.yes:
        confirm = input("Удалить этих пользователей? (yes/[no]): ").strip().lower()
        if confirm != "yes":
            print("Отменено.")
            return

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.executemany("DELETE FROM users WHERE id = ?", [(i,) for i in to_delete_ids])
        conn.commit()

    print(f"Удалено пользователей: {len(to_delete_ids)}")


if __name__ == "__main__":
    main()

