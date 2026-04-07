"""
Менеджер миграций базы данных.
"""
import os
import importlib.util
import logging
import inspect
from collections import defaultdict
from typing import List, Dict, Optional
from app.database.connection import get_db_connection
import sqlite3

logger = logging.getLogger(__name__)


class MigrationManager:
    """Класс для управления миграциями базы данных."""
    
    def __init__(self):
        """Инициализация менеджера миграций."""
        self.migrations_dir = os.path.join(
            os.path.dirname(__file__),
            'versions'
        )
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self):
        """Создает таблицу для отслеживания выполненных миграций."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        version TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при создании таблицы миграций: {e}")
            raise
    
    def get_applied_migrations(self) -> List[str]:
        """
        Получает список примененных миграций.
        
        Returns:
            Список версий примененных миграций
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT version FROM schema_migrations ORDER BY version')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении списка миграций: {e}")
            return []
    
    def is_migration_applied(self, version: str) -> bool:
        """
        Проверяет, применена ли миграция.
        
        Args:
            version: Версия миграции
            
        Returns:
            True если миграция применена
        """
        return version in self.get_applied_migrations()
    
    def mark_migration_applied(self, version: str, name: str):
        """
        Отмечает миграцию как примененную.
        
        Args:
            version: Версия миграции
            name: Название миграции
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO schema_migrations (version, name)
                    VALUES (?, ?)
                ''', (version, name))
                conn.commit()
        except sqlite3.IntegrityError:
            # Миграция уже применена
            pass
        except Exception as e:
            logger.error(f"Ошибка при отметке миграции {version}: {e}")
            raise
    
    def mark_migration_rolled_back(self, version: str):
        """
        Удаляет запись о примененной миграции (для rollback).
        
        Args:
            version: Версия миграции
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM schema_migrations WHERE version = ?', (version,))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при откате миграции {version}: {e}")
            raise
    
    def get_migration_files(self) -> List[Dict[str, str]]:
        """
        Получает список файлов миграций.
        
        Returns:
            Список словарей с информацией о миграциях
        """
        migrations = []
        
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir, exist_ok=True)
            return migrations
        
        for filename in sorted(os.listdir(self.migrations_dir)):
            if filename.endswith('.py') and filename.startswith('0'):
                # Формат: 001_initial.py
                parts = filename[:-3].split('_', 1)
                if len(parts) == 2:
                    migrations.append({
                        'version': parts[0],
                        'name': parts[1],
                        'filename': filename
                    })

        # Защита от конфликтов вида 043_x.py и 043_y.py:
        # у нас version является уникальным ключом в schema_migrations.
        grouped = defaultdict(list)
        for migration in migrations:
            grouped[migration['version']].append(migration['filename'])
        conflicts = {ver: files for ver, files in grouped.items() if len(files) > 1}
        if conflicts:
            conflict_msg = "; ".join(
                f"{ver}: {', '.join(sorted(files))}" for ver, files in sorted(conflicts.items())
            )
            raise RuntimeError(
                "Обнаружен конфликт версий миграций (дубликаты version): "
                f"{conflict_msg}. Исправьте имена файлов миграций."
            )
        
        return migrations

    def _load_migration_module(self, filename: str):
        """
        Загружает модуль миграции по пути файла.

        ВАЖНО: имена миграций начинаются с цифр (001_initial.py), их нельзя импортировать
        через importlib.import_module() по имени модуля. Поэтому используем spec_from_file_location.
        """
        migration_path = os.path.join(self.migrations_dir, filename)
        module_name = f"migration_{filename[:-3]}"
        spec = importlib.util.spec_from_file_location(module_name, migration_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Не удалось загрузить миграцию из файла: {migration_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    def migrate(self, target_version: Optional[str] = None) -> List[str]:
        """
        Применяет все непримененные миграции.
        
        Args:
            target_version: Целевая версия (если None, применяются все)
            
        Returns:
            Список примененных миграций
        """
        applied = self.get_applied_migrations()
        migrations = self.get_migration_files()
        applied_migrations = []
        
        for migration in migrations:
            if migration['version'] in applied:
                continue
            
            if target_version and migration['version'] > target_version:
                break
            
            try:
                logger.info(f"Применение миграции {migration['version']}: {migration['name']}")
                
                # Загружаем модуль миграции по пути файла (имя начинается с цифры)
                module = self._load_migration_module(migration['filename'])
                
                # Выполняем миграцию
                if hasattr(module, 'up'):
                    up_fn = getattr(module, 'up')
                    sig = inspect.signature(up_fn)
                    if len(sig.parameters) >= 1:
                        # Некоторые миграции ожидают conn (sqlite3.Connection)
                        with get_db_connection() as conn:
                            up_fn(conn)
                    else:
                        up_fn()
                else:
                    logger.warning(f"Миграция {migration['version']} не имеет функции up()")
                    continue
                
                # Отмечаем как примененную
                self.mark_migration_applied(migration['version'], migration['name'])
                applied_migrations.append(migration['version'])
                
                logger.info(f"Миграция {migration['version']} успешно применена")
            except Exception as e:
                logger.error(f"Ошибка при применении миграции {migration['version']}: {e}")
                raise
        
        return applied_migrations
    
    def rollback(self, target_version: Optional[str] = None) -> List[str]:
        """
        Откатывает миграции.
        
        Args:
            target_version: Целевая версия (если None, откатывается последняя)
            
        Returns:
            Список откатанных миграций
        """
        applied = self.get_applied_migrations()
        migrations = self.get_migration_files()
        rolled_back = []
        
        # Откатываем в обратном порядке
        for migration in reversed(migrations):
            if migration['version'] not in applied:
                continue
            
            if target_version and migration['version'] <= target_version:
                break
            
            try:
                logger.info(f"Откат миграции {migration['version']}: {migration['name']}")
                
                # Загружаем модуль миграции по пути файла (имя начинается с цифры)
                module = self._load_migration_module(migration['filename'])
                
                # Выполняем откат
                if hasattr(module, 'down'):
                    down_fn = getattr(module, 'down')
                    sig = inspect.signature(down_fn)
                    if len(sig.parameters) >= 1:
                        with get_db_connection() as conn:
                            down_fn(conn)
                    else:
                        down_fn()
                else:
                    logger.warning(f"Миграция {migration['version']} не имеет функции down()")
                    continue
                
                # Удаляем запись о применении
                self.mark_migration_rolled_back(migration['version'])
                rolled_back.append(migration['version'])
                
                logger.info(f"Миграция {migration['version']} успешно откачена")
            except Exception as e:
                logger.error(f"Ошибка при откате миграции {migration['version']}: {e}")
                raise
        
        return rolled_back
    
    def status(self) -> Dict:
        """
        Получает статус миграций.
        
        Returns:
            Словарь со статусом миграций
        """
        applied = self.get_applied_migrations()
        migrations = self.get_migration_files()
        
        status_list = []
        for migration in migrations:
            status_list.append({
                'version': migration['version'],
                'name': migration['name'],
                'applied': migration['version'] in applied
            })
        
        return {
            'total': len(migrations),
            'applied': len(applied),
            'pending': len(migrations) - len(applied),
            'migrations': status_list
        }

