#!/usr/bin/env python3
"""
Скрипт для применения миграций базы данных.
Перед миграцией создаёт бекап БД в папку database/backups.
"""
import sys
import os
import shutil
import subprocess
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.migrations.manager import MigrationManager
from app.database.migrations.postgres_manager import PostgresMigrationManager
from app.database.connection import _get_db_driver
from app.config import Config
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def create_pre_migration_backup(db_path: str) -> str:
    """Создаёт бекап БД перед миграцией в папку backups рядом с БД. Возвращает путь к бекапу."""
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(db_path)), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"База данных не найдена: {db_path}")
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"service_center.db.backup_pre_migration_{ts}"
    backup_path = os.path.join(backup_dir, backup_filename)
    shutil.copy2(db_path, backup_path)
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    logger.info(f"Создан бекап БД: {backup_path} ({size_mb:.2f} MB)")
    return backup_path


def create_pre_migration_pg_backup(database_url: str) -> str:
    """Создаёт pg_dump перед миграцией PostgreSQL."""
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(Config.DATABASE_PATH)), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f"postgres.backup_pre_migration_{ts}.dump")
    env = os.environ.copy()
    subprocess.run(
        ["pg_dump", "--format=custom", "--file", backup_path, database_url],
        check=True,
        env=env,
    )
    size_mb = os.path.getsize(backup_path) / (1024 * 1024)
    logger.info(f"Создан бекап PostgreSQL: {backup_path} ({size_mb:.2f} MB)")
    return backup_path


def main():
    """Применяет все непримененные миграции."""
    print("=" * 80)
    print("ПРИМЕНЕНИЕ МИГРАЦИЙ БАЗЫ ДАННЫХ")
    print("=" * 80)
    print()
    
    try:
        driver = _get_db_driver()
        manager = PostgresMigrationManager() if driver == 'postgres' else MigrationManager()
        
        # Показываем статус
        status = manager.status()
        print(f"Всего миграций: {status['total']}")
        print(f"Применено: {status['applied']}")
        print(f"Ожидают применения: {status['pending']}")
        print()
        
        if status['pending'] <= 0:
            print("[OK] Все миграции уже применены (нет неприменённых)")
            return
        
        # Показываем непримененные миграции
        pending = [m for m in status['migrations'] if not m['applied']]
        if pending:
            print("Непримененные миграции:")
            for m in pending:
                print(f"  - {m['version']}: {m['name']}")
            print()
        
        # Бекап перед миграцией (обязательно)
        print("Создание бекапа БД перед миграцией...")
        if driver == 'postgres':
            database_url = os.environ.get('DATABASE_URL', Config.DATABASE_URL)
            if not database_url:
                raise RuntimeError("DATABASE_URL не задан для PostgreSQL")
            backup_path = create_pre_migration_pg_backup(database_url)
        else:
            db_path = os.environ.get('DATABASE_PATH', Config.DATABASE_PATH)
            backup_path = create_pre_migration_backup(db_path)
        print(f"[OK] Бекап: {backup_path}")
        print()
        
        # Применяем миграции
        print("Применение миграций...")
        applied = manager.migrate()
        
        if applied:
            print(f"\n[OK] Успешно применено {len(applied)} миграций:")
            for version in applied:
                print(f"  - {version}")
        else:
            print("\n[WARN] Миграции не были применены")
            
    except Exception as e:
        logger.error(f"Ошибка при применении миграций: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
