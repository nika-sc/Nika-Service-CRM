"""
Сервис для автоматического резервного копирования базы данных.
"""
import os
import shutil
import logging
from datetime import datetime, date
from typing import Optional, List
from app.utils.datetime_utils import get_moscow_now_str
from pathlib import Path
from app.config import Config
from app.database.connection import DATABASE_PATH
from app.services.action_log_service import ActionLogService

logger = logging.getLogger(__name__)


class BackupService:
    """Сервис для создания и управления бэкапами БД."""
    
    BACKUP_DIR = os.path.join('database', 'backups')
    
    @staticmethod
    def ensure_backup_dir():
        """Создает директорию для бэкапов, если её нет."""
        os.makedirs(BackupService.BACKUP_DIR, exist_ok=True)
    
    @staticmethod
    def create_backup(backup_name: Optional[str] = None) -> str:
        """
        Создает бэкап БД и возвращает путь к файлу.
        
        Args:
            backup_name: Имя бэкапа (опционально). Если не указано, используется timestamp.
        
        Returns:
            str: Путь к созданному файлу бэкапа
        """
        BackupService.ensure_backup_dir()
        
        if not os.path.exists(DATABASE_PATH):
            raise FileNotFoundError(f"База данных не найдена: {DATABASE_PATH}")
        
        if backup_name:
            backup_filename = f"service_center.db.backup_{backup_name}"
        else:
            timestamp = get_moscow_now_str('%Y%m%d_%H%M%S')
            backup_filename = f"service_center.db.backup_{timestamp}"
        
        backup_path = os.path.join(BackupService.BACKUP_DIR, backup_filename)
        
        try:
            # Копируем БД
            shutil.copy2(DATABASE_PATH, backup_path)
            
            # Получаем размер файла
            backup_size = os.path.getsize(backup_path)
            backup_size_mb = backup_size / (1024 * 1024)
            
            logger.info(
                f"Создан бэкап БД: {backup_path} "
                f"({backup_size_mb:.2f} MB)"
            )

            # Логируем создание бэкапа
            try:
                ActionLogService.log_action(
                    user_id=None,  # Системная операция
                    username='system',
                    action_type='create',
                    entity_type='backup',
                    entity_id=None,
                    description=f"Создан бэкап базы данных",
                    details={
                        'backup_path': backup_path,
                        'backup_size_mb': round(backup_size_mb, 2),
                        'backup_name': backup_name
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать создание бэкапа: {e}")

            return backup_path
        except Exception as e:
            logger.error(f"Ошибка при создании бэкапа: {e}", exc_info=True)
            raise
    
    @staticmethod
    def cleanup_old_backups(keep: int = 30) -> int:
        """
        Удаляет старые бэкапы, оставляя только последние N.
        
        Args:
            keep: Количество бэкапов для сохранения (по умолчанию 30)
        
        Returns:
            int: Количество удаленных бэкапов
        """
        BackupService.ensure_backup_dir()
        
        if not os.path.exists(BackupService.BACKUP_DIR):
            return 0
        
        # Получаем список всех бэкапов
        backups = []
        for filename in os.listdir(BackupService.BACKUP_DIR):
            if filename.startswith('service_center.db.backup_'):
                filepath = os.path.join(BackupService.BACKUP_DIR, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                    backups.append((mtime, filepath, filename))
                except OSError:
                    continue
        
        # Сортируем по дате изменения (новые первыми)
        backups.sort(reverse=True)
        
        # Удаляем старые бэкапы
        deleted_count = 0
        for mtime, filepath, filename in backups[keep:]:
            try:
                os.remove(filepath)
                deleted_count += 1
                logger.info(f"Удален старый бэкап: {filename}")
            except OSError as e:
                logger.warning(f"Не удалось удалить бэкап {filename}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Удалено старых бэкапов: {deleted_count}")
        
        return deleted_count
    
    @staticmethod
    def get_backup_list(limit: Optional[int] = None) -> List[dict]:
        """
        Возвращает список бэкапов с информацией о них.
        
        Args:
            limit: Максимальное количество бэкапов для возврата
        
        Returns:
            List[dict]: Список словарей с информацией о бэкапах
        """
        BackupService.ensure_backup_dir()
        
        if not os.path.exists(BackupService.BACKUP_DIR):
            return []
        
        backups = []
        for filename in os.listdir(BackupService.BACKUP_DIR):
            if filename.startswith('service_center.db.backup_'):
                filepath = os.path.join(BackupService.BACKUP_DIR, filename)
                try:
                    stat = os.stat(filepath)
                    size = stat.st_size
                    size_mb = size / (1024 * 1024)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    
                    backups.append({
                        'filename': filename,
                        'path': filepath,
                        'size': size,
                        'size_mb': round(size_mb, 2),
                        'created_at': mtime.isoformat(),
                        'created_at_display': mtime.strftime('%d.%m.%Y %H:%M:%S')
                    })
                except OSError:
                    continue
        
        # Сортируем по дате (новые первыми)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        if limit:
            backups = backups[:limit]
        
        return backups
    
    @staticmethod
    def restore_backup(backup_path: str, create_backup_before_restore: bool = True) -> bool:
        """
        Восстанавливает БД из бэкапа.
        
        Args:
            backup_path: Путь к файлу бэкапа
            create_backup_before_restore: Создать бэкап текущей БД перед восстановлением
        
        Returns:
            bool: True если восстановление успешно
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Файл бэкапа не найден: {backup_path}")
        
        # Создаем бэкап текущей БД перед восстановлением
        if create_backup_before_restore and os.path.exists(DATABASE_PATH):
            try:
                timestamp = get_moscow_now_str('%Y%m%d_%H%M%S')
                pre_restore_backup = BackupService.create_backup(f"before_restore_{timestamp}")
                logger.info(f"Создан бэкап перед восстановлением: {pre_restore_backup}")
            except Exception as e:
                logger.warning(f"Не удалось создать бэкап перед восстановлением: {e}")
        
        try:
            # Копируем бэкап на место БД
            shutil.copy2(backup_path, DATABASE_PATH)
            logger.info(f"БД восстановлена из бэкапа: {backup_path}")

            # Логируем восстановление бэкапа
            try:
                ActionLogService.log_action(
                    user_id=None,  # Системная операция
                    username='system',
                    action_type='restore',
                    entity_type='backup',
                    entity_id=None,
                    description=f"Восстановлена база данных из бэкапа",
                    details={
                        'backup_path': backup_path,
                        'create_backup_before_restore': create_backup_before_restore
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать восстановление бэкапа: {e}")

            return True
        except Exception as e:
            logger.error(f"Ошибка при восстановлении БД: {e}", exc_info=True)
            raise
    
    @staticmethod
    def get_backup_info(backup_path: str) -> dict:
        """
        Возвращает информацию о бэкапе.
        
        Args:
            backup_path: Путь к файлу бэкапа
        
        Returns:
            dict: Информация о бэкапе
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Файл бэкапа не найден: {backup_path}")
        
        stat = os.stat(backup_path)
        size = stat.st_size
        size_mb = size / (1024 * 1024)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        
        return {
            'path': backup_path,
            'filename': os.path.basename(backup_path),
            'size': size,
            'size_mb': round(size_mb, 2),
            'created_at': mtime.isoformat(),
            'created_at_display': mtime.strftime('%d.%m.%Y %H:%M:%S')
        }
    
    @staticmethod
    def delete_backup(backup_path: str) -> bool:
        """
        Удаляет бэкап.
        
        Args:
            backup_path: Путь к файлу бэкапа
        
        Returns:
            bool: True если удаление успешно
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Файл бэкапа не найден: {backup_path}")
        
        try:
            os.remove(backup_path)
            logger.info(f"Удален бэкап: {backup_path}")
            return True
        except OSError as e:
            logger.error(f"Ошибка при удалении бэкапа: {e}", exc_info=True)
            raise
