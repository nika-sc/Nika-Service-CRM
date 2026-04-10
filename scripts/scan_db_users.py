#!/usr/bin/env python3
"""Сканирует все .db в database/ и database/backups/, выводит файлы и кол-во users."""
import os
import sqlite3

base = os.path.join(os.path.dirname(__file__), "..", "database")
results = []

for root, _dirs, files in os.walk(base):
    for f in files:
        if f == "add_indexes.py" or not (f.startswith("service_center") or f.endswith(".db")):
            continue
        path = os.path.join(root, f)
        rel = os.path.relpath(path, base)
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cur.fetchone():
                users = -1  # нет таблицы
            else:
                cur.execute("SELECT COUNT(*) FROM users")
                users = cur.fetchone()[0]
            try:
                cur.execute("SELECT COUNT(*) FROM customers")
                customers = cur.fetchone()[0]
            except Exception:
                customers = "?"
            try:
                cur.execute("SELECT COUNT(*) FROM services")
                services = cur.fetchone()[0]
            except Exception:
                services = "?"
            conn.close()
            results.append((rel, users, customers, services))
        except Exception as e:
            results.append((rel, f"err: {e}", None, None))

print("File (relative to database/)                    | users | customers | services")
print("-" * 85)
for rel, u, c, s in sorted(results, key=lambda x: (0 if isinstance(x[1], int) else 1, x[1] if isinstance(x[1], int) else 0)):
    c = c if c is not None else "?"
    s = s if s is not None else "?"
    print(f"{rel:<48} | {str(u):>5} | {str(c):>9} | {str(s):>8}")

print()
print("=== Файлы БЕЗ пользователей (users = 0 или нет таблицы) ===")
for rel, u, c, s in sorted(results, key=lambda x: x[0]):
    if u == 0 or u == -1:
        print(f"  {rel}")
