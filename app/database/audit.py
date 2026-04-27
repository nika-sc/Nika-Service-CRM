"""
Модуль для аудита базы данных и анализа legacy кода.
"""
import re
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)

# Допустимые символы для имён таблиц/индексов SQLite (защита от SQL-инъекций)
_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_sqlite_identifier(name: str) -> bool:
    """Проверяет допустимость имени для использования в PRAGMA/SQL."""
    return bool(name and isinstance(name, str) and _IDENTIFIER_RE.match(name))


def get_all_tables() -> List[str]:
    """
    Получает список всех таблиц в БД.
    
    Returns:
        Список имен таблиц
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Ошибка при получении списка таблиц: {e}")
        return []


def get_table_structure(table_name: str) -> List[Dict]:
    """
    Получает структуру таблицы.
    
    Args:
        table_name: Имя таблицы
        
    Returns:
        Список словарей с информацией о колонках
    """
    if not _validate_sqlite_identifier(table_name):
        logger.warning(f"Недопустимое имя таблицы: {table_name!r}")
        return []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    'cid': row[0],
                    'name': row[1],
                    'type': row[2],
                    'notnull': row[3],
                    'default_value': row[4],
                    'pk': row[5]
                })
            return columns
    except Exception as e:
        logger.error(f"Ошибка при получении структуры таблицы {table_name}: {e}")
        return []


def get_table_indexes(table_name: str) -> List[Dict]:
    """
    Получает индексы таблицы.
    
    Args:
        table_name: Имя таблицы
        
    Returns:
        Список словарей с информацией об индексах
    """
    if not _validate_sqlite_identifier(table_name):
        logger.warning(f"Недопустимое имя таблицы: {table_name!r}")
        return []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = []
            for row in cursor.fetchall():
                index_name = row[1]
                if not _validate_sqlite_identifier(index_name):
                    continue
                cursor.execute(f"PRAGMA index_info({index_name})")
                columns = [col[2] for col in cursor.fetchall()]
                indexes.append({
                    'name': index_name,
                    'unique': row[2] == 1,
                    'columns': columns
                })
            return indexes
    except Exception as e:
        logger.error(f"Ошибка при получении индексов таблицы {table_name}: {e}")
        return []


def get_foreign_keys(table_name: str) -> List[Dict]:
    """
    Получает внешние ключи таблицы.
    
    Args:
        table_name: Имя таблицы
        
    Returns:
        Список словарей с информацией о внешних ключах
    """
    if not _validate_sqlite_identifier(table_name):
        logger.warning(f"Недопустимое имя таблицы: {table_name!r}")
        return []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            fks = []
            for row in cursor.fetchall():
                fks.append({
                    'id': row[0],
                    'seq': row[1],
                    'table': row[2],
                    'from': row[3],
                    'to': row[4],
                    'on_update': row[5],
                    'on_delete': row[6],
                    'match': row[7]
                })
            return fks
    except Exception as e:
        logger.error(f"Ошибка при получении внешних ключей таблицы {table_name}: {e}")
        return []


def analyze_database() -> Dict:
    """
    Проводит полный аудит базы данных.
    
    Returns:
        Словарь с результатами аудита
    """
    tables = get_all_tables()
    result = {
        'tables': {},
        'total_tables': len(tables),
        'missing_indexes': [],
        'missing_foreign_keys': [],
        'recommendations': []
    }
    
    for table_name in tables:
        structure = get_table_structure(table_name)
        indexes = get_table_indexes(table_name)
        foreign_keys = get_foreign_keys(table_name)
        
        result['tables'][table_name] = {
            'columns': structure,
            'indexes': indexes,
            'foreign_keys': foreign_keys,
            'column_count': len(structure),
            'index_count': len(indexes),
            'fk_count': len(foreign_keys)
        }
        
        # Проверка на потенциальные проблемы
        pk_columns = [col['name'] for col in structure if col['pk']]
        if not pk_columns:
            result['recommendations'].append(f"Таблица {table_name} не имеет PRIMARY KEY")
        
        # Проверка индексов для часто используемых полей
        if table_name == 'orders':
            indexed_columns = set()
            for idx in indexes:
                indexed_columns.update(idx['columns'])
            
            important_columns = ['customer_id', 'device_id', 'status_id', 'created_at']
            for col in important_columns:
                if col not in indexed_columns:
                    result['missing_indexes'].append(f"{table_name}.{col}")
        
        if table_name == 'customers':
            indexed_columns = set()
            for idx in indexes:
                indexed_columns.update(idx['columns'])
            
            if 'phone' not in indexed_columns:
                result['missing_indexes'].append(f"{table_name}.phone")
    
    return result


def get_table_row_count(table_name: str) -> int:
    """
    Получает количество строк в таблице.
    
    Args:
        table_name: Имя таблицы
        
    Returns:
        Количество строк
    """
    if not _validate_sqlite_identifier(table_name):
        logger.warning(f"Недопустимое имя таблицы: {table_name!r}")
        return 0
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Ошибка при подсчете строк в таблице {table_name}: {e}")
        return 0

