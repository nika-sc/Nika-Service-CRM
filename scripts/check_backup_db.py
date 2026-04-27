#!/usr/bin/env python3
"""Проверка содержимого бекапа БД: пользователи, склад, услуги."""
import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else "database/service_center.db.backup_before_import_20260302_224926"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Список таблиц и количество записей
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print("=== Таблицы и количество записей ===\n")
for t in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        n = cur.fetchone()[0]
        print(f"  {t}: {n}")
    except Exception as e:
        print(f"  {t}: ошибка - {e}")

# Детально: пользователи
print("\n=== Пользователи (users) ===")
if "users" in tables:
    cur.execute("SELECT COUNT(*) FROM users")
    print(f"Записей: {cur.fetchone()[0]}")
    cur.execute("SELECT id, username, display_name, role FROM users LIMIT 5")
    for row in cur.fetchall():
        print(f"  {row}")
else:
    print("Таблица users отсутствует")

# Детально: склад (parts, part_categories, stock_movements и т.д.)
print("\n=== Склад ===")
warehouse_tables = ["parts", "part_categories", "stock_movements", "purchases", "warehouse_logs", "suppliers"]
for t in warehouse_tables:
    if t in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        print(f"  {t}: {cur.fetchone()[0]}")
    else:
        print(f"  {t}: таблица отсутствует")

# Детально: услуги
print("\n=== Услуги (services) ===")
if "services" in tables:
    cur.execute("SELECT COUNT(*) FROM services")
    print(f"Записей: {cur.fetchone()[0]}")
    cur.execute("SELECT id, name, price FROM services LIMIT 3")
    for row in cur.fetchall():
        print(f"  {row}")
else:
    print("Таблица services отсутствует")

# Клиенты
print("\n=== Клиенты (customers) ===")
if "customers" in tables:
    cur.execute("SELECT COUNT(*) FROM customers")
    print(f"Записей: {cur.fetchone()[0]}")
else:
    print("Таблица customers отсутствует")

conn.close()
print("\nГотово.")
