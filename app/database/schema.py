"""
Определение схемы базы данных в коде.

Этот модуль содержит функции для создания и обновления схемы БД.
"""
import logging
from typing import Dict, List
from app.database.connection import get_db_connection
from app.database.audit import (
    get_all_tables,
    get_table_structure,
    get_table_indexes,
    get_foreign_keys
)

logger = logging.getLogger(__name__)


def get_schema_definition() -> Dict:
    """
    Получает определение схемы БД.
    
    Returns:
        Словарь с описанием схемы БД
    """
    tables = get_all_tables()
    schema = {
        'tables': {},
        'relationships': []
    }
    
    for table_name in tables:
        structure = get_table_structure(table_name)
        indexes = get_table_indexes(table_name)
        foreign_keys = get_foreign_keys(table_name)
        
        schema['tables'][table_name] = {
            'columns': structure,
            'indexes': indexes,
            'foreign_keys': foreign_keys
        }
        
        # Добавляем связи
        for fk in foreign_keys:
            schema['relationships'].append({
                'from_table': table_name,
                'from_column': fk['from'],
                'to_table': fk['table'],
                'to_column': fk['to'],
                'on_delete': fk['on_delete'],
                'on_update': fk['on_update']
            })
    
    return schema


def validate_schema() -> List[str]:
    """
    Проверяет целостность схемы БД.
    
    Returns:
        Список найденных проблем (пустой список, если проблем нет)
    """
    issues = []
    tables = get_all_tables()
    
    # Проверяем наличие обязательных таблиц
    required_tables = [
        'customers', 'devices', 'orders', 'order_statuses',
        'users', 'services', 'parts', 'payments'
    ]
    
    for table in required_tables:
        if table not in tables:
            issues.append(f"Отсутствует обязательная таблица: {table}")
    
    # Проверяем наличие PRIMARY KEY в каждой таблице
    for table_name in tables:
        structure = get_table_structure(table_name)
        has_pk = any(col['pk'] for col in structure)
        if not has_pk:
            issues.append(f"Таблица {table_name} не имеет PRIMARY KEY")
    
    # Проверяем внешние ключи
    for table_name in tables:
        foreign_keys = get_foreign_keys(table_name)
        for fk in foreign_keys:
            # Проверяем, что таблица, на которую ссылается FK, существует
            if fk['table'] not in tables:
                issues.append(
                    f"Таблица {table_name} ссылается на несуществующую таблицу {fk['table']}"
                )
    
    return issues


def get_table_dependencies(table_name: str) -> List[str]:
    """
    Получает список таблиц, от которых зависит указанная таблица.
    
    Args:
        table_name: Имя таблицы
        
    Returns:
        Список имен зависимых таблиц
    """
    foreign_keys = get_foreign_keys(table_name)
    dependencies = []
    
    for fk in foreign_keys:
        if fk['table'] not in dependencies:
            dependencies.append(fk['table'])
            # Рекурсивно получаем зависимости зависимостей
            sub_deps = get_table_dependencies(fk['table'])
            for dep in sub_deps:
                if dep not in dependencies:
                    dependencies.append(dep)
    
    return dependencies


def get_table_dependents(table_name: str) -> List[str]:
    """
    Получает список таблиц, которые зависят от указанной таблицы.
    
    Args:
        table_name: Имя таблицы
        
    Returns:
        Список имен зависимых таблиц
    """
    dependents = []
    all_tables = get_all_tables()
    
    for other_table in all_tables:
        if other_table == table_name:
            continue
        
        foreign_keys = get_foreign_keys(other_table)
        for fk in foreign_keys:
            if fk['table'] == table_name:
                if other_table not in dependents:
                    dependents.append(other_table)
                # Рекурсивно получаем зависимые от зависимых
                sub_deps = get_table_dependents(other_table)
                for dep in sub_deps:
                    if dep not in dependents:
                        dependents.append(dep)
    
    return dependents


def get_creation_order() -> List[str]:
    """
    Получает порядок создания таблиц с учетом зависимостей.
    
    Returns:
        Список имен таблиц в порядке создания
    """
    tables = get_all_tables()
    created = []
    remaining = list(tables)
    
    while remaining:
        progress = False
        
        for table_name in list(remaining):
            dependencies = get_table_dependencies(table_name)
            # Если все зависимости уже созданы (или их нет)
            if all(dep in created for dep in dependencies):
                created.append(table_name)
                remaining.remove(table_name)
                progress = True
        
        if not progress:
            # Если не удалось создать ни одну таблицу, значит есть циклические зависимости
            logger.warning(f"Обнаружены циклические зависимости. Оставшиеся таблицы: {remaining}")
            # Добавляем оставшиеся таблицы в произвольном порядке
            created.extend(remaining)
            break
    
    return created


def get_deletion_order() -> List[str]:
    """
    Получает порядок удаления таблиц с учетом зависимостей.
    
    Returns:
        Список имен таблиц в порядке удаления (обратный порядку создания)
    """
    creation_order = get_creation_order()
    return list(reversed(creation_order))

