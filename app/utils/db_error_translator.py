"""
Утилита для перевода ошибок SQLite на русский язык.
"""
import sqlite3
import re


def translate_db_error(error: Exception) -> str:
    """
    Переводит ошибку SQLite на русский язык.
    
    Args:
        error: Исключение SQLite
        
    Returns:
        Переведенное сообщение об ошибке
    """
    if not isinstance(error, (sqlite3.Error, Exception)):
        return str(error)
    
    error_msg = str(error)
    
    # UNIQUE constraint failed
    if 'UNIQUE constraint failed' in error_msg:
        # Извлекаем название таблицы и колонки
        match = re.search(r'UNIQUE constraint failed: (\w+)\.(\w+)', error_msg)
        if match:
            table_name, column_name = match.groups()
            
            # Переводы названий таблиц
            table_translations = {
                'customers': 'клиентов',
                'orders': 'заявок',
                'devices': 'устройств',
                'parts': 'товаров',
                'users': 'пользователей',
                'services': 'услуг',
                'order_statuses': 'статусов заявок',
                'device_types': 'типов устройств',
                'device_brands': 'брендов устройств',
                'transaction_categories': 'категорий транзакций',
                'shop_sales': 'продаж',
                'cash_transactions': 'кассовых операций'
            }
            
            # Переводы названий колонок
            column_translations = {
                'phone': 'номер телефона',
                'email': 'email',
                'name': 'название',
                'order_id': 'номер заявки',
                'part_number': 'артикул',
                'username': 'имя пользователя',
                'serial_number': 'серийный номер',
                'code': 'код',
                'sku': 'артикул'
            }
            
            table_ru = table_translations.get(table_name, table_name)
            column_ru = column_translations.get(column_name, column_name)
            
            # Специальные сообщения для известных комбинаций
            if table_name == 'customers' and column_name == 'phone':
                return "Клиент с таким номером телефона уже существует"
            elif table_name == 'customers' and column_name == 'email':
                return "Клиент с таким email уже существует"
            elif table_name == 'users' and column_name == 'username':
                return "Пользователь с таким именем уже существует"
            elif table_name == 'parts' and column_name == 'part_number':
                return "Товар с таким артикулом уже существует"
            elif table_name == 'orders' and column_name == 'order_id':
                return "Заявка с таким номером уже существует"
            
            return f"Запись с таким {column_ru} уже существует"
        
        return "Нарушено ограничение уникальности"
    
    # FOREIGN KEY constraint failed
    if 'FOREIGN KEY constraint failed' in error_msg:
        match = re.search(r'FOREIGN KEY constraint failed.*?(\w+)\.(\w+)', error_msg)
        if match:
            table_name, column_name = match.groups()
            table_translations = {
                'orders': 'заявок',
                'devices': 'устройств',
                'customers': 'клиентов',
                'parts': 'товаров'
            }
            table_ru = table_translations.get(table_name, table_name)
            return f"Невозможно выполнить операцию: связанная запись в таблице {table_ru} не найдена"
        return "Нарушено ограничение внешнего ключа"
    
    # NOT NULL constraint failed
    if 'NOT NULL constraint failed' in error_msg:
        match = re.search(r'NOT NULL constraint failed: (\w+)\.(\w+)', error_msg)
        if match:
            table_name, column_name = match.groups()
            column_translations = {
                'name': 'название',
                'phone': 'телефон',
                'order_id': 'номер заявки',
                'customer_id': 'клиент',
                'device_id': 'устройство'
            }
            column_ru = column_translations.get(column_name, column_name)
            return f"Обязательное поле '{column_ru}' не заполнено"
        return "Обязательное поле не заполнено"
    
    # CHECK constraint failed
    if 'CHECK constraint failed' in error_msg:
        return "Нарушено ограничение проверки данных"
    
    # SQL syntax error
    if 'syntax error' in error_msg.lower():
        return "Ошибка синтаксиса SQL запроса"
    
    # Database is locked
    if 'database is locked' in error_msg.lower():
        return "База данных заблокирована. Попробуйте позже"
    
    # Disk I/O error
    if 'disk i/o error' in error_msg.lower():
        return "Ошибка чтения/записи на диск"
    
    # Out of memory
    if 'out of memory' in error_msg.lower():
        return "Недостаточно памяти"
    
    # Если не нашли специфичный перевод, возвращаем общее сообщение
    return f"Ошибка базы данных: {error_msg}"

