"""
Менеджер миграций PostgreSQL.
"""
import logging
import os
from typing import Dict, List

from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class PostgresMigrationManager:
    """Применяет SQL-миграции из postgres_versions/."""

    def __init__(self):
        self.migrations_dir = os.path.join(os.path.dirname(__file__), "postgres_versions")
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations_pg (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def get_applied_migrations(self) -> List[str]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations_pg ORDER BY version")
            rows = cursor.fetchall()
            return [row[0] for row in rows]

    def get_migration_files(self) -> List[Dict[str, str]]:
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir, exist_ok=True)
            return []

        migrations = []
        for filename in sorted(os.listdir(self.migrations_dir)):
            if not filename.endswith(".sql"):
                continue
            parts = filename[:-4].split("_", 1)
            if len(parts) != 2:
                continue
            migrations.append(
                {
                    "version": parts[0],
                    "name": parts[1],
                    "filename": filename,
                }
            )
        return migrations

    def status(self) -> Dict:
        applied = set(self.get_applied_migrations())
        migrations = self.get_migration_files()
        result = []
        for migration in migrations:
            result.append(
                {
                    "version": migration["version"],
                    "name": migration["name"],
                    "applied": migration["version"] in applied,
                }
            )
        return {
            "total": len(migrations),
            "applied": len(applied),
            "pending": len(migrations) - len(applied),
            "migrations": result,
        }

    def migrate(self) -> List[str]:
        applied_versions = set(self.get_applied_migrations())
        migrations = self.get_migration_files()
        executed = []

        for migration in migrations:
            if migration["version"] in applied_versions:
                continue
            path = os.path.join(self.migrations_dir, migration["filename"])
            logger.info("Applying PostgreSQL migration %s: %s", migration["version"], migration["name"])
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                cursor.execute(
                    "INSERT INTO schema_migrations_pg (version, name) VALUES (?, ?)",
                    (migration["version"], migration["name"]),
                )
                conn.commit()
            executed.append(migration["version"])
        return executed
