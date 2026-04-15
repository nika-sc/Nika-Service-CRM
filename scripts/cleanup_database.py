"""
Скрипт полной очистки базы данных (кроме настроек и шаблонов).

Удаляет:
- Все заявки и связанные данные (комментарии, вложения, задачи, шаблоны заявок)
- Все оплаты, кассовые операции, чеки, продажи в магазине
- Закупки, инвентаризации, поставщики, логи действий, зарплата
- Уведомления, токены клиентов (портал), история смены ролей
- Клиентов, устройства, типы устройств, бренды устройств
- Услуги, статусы заявок
- Пользователей (кроме одного админа), мастеров, менеджеров
- Симптомы, теги внешнего вида, товары и каталоги товаров
(аналитика и отчёты строятся из этих данных — после очистки будут пустыми)

Оставляет:
- Настройки (general_settings, system_settings)
- Статьи приходов и расходов (transaction_categories)
- Шаблоны распечатки квитанций и шаблоны писем (print_templates)
- Права доступа (permissions, role_permissions) и одного пользователя admin
- schema_migrations
"""
import sqlite3
import sys
import os
import shutil
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.config import Config

DB_PATH = Config.DATABASE_PATH
BACKUP_DIR = os.path.join(os.path.dirname(DB_PATH), 'backups')


def create_backup():
    """Создает резервную копию БД перед очисткой."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'backup_before_cleanup_{timestamp}.db')
    
    print(f"\n[1/5] Создание резервной копии...")
    print(f"      Источник: {DB_PATH}")
    print(f"      Копия: {backup_path}")
    
    shutil.copy2(DB_PATH, backup_path)
    print(f"      [OK] Резервная копия создана\n")
    
    return backup_path


def get_table_count(cursor, table_name):
    """Получает количество записей в таблице."""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    except:
        return 0


def show_statistics(cursor, title, tables):
    """Показывает статистику по таблицам."""
    print(f"\n{title}:")
    total = 0
    for table in tables:
        count = get_table_count(cursor, table)
        total += count
        print(f"  {table:<40} {count:>8} записей")
    print(f"  {'ИТОГО':<40} {total:>8} записей")
    return total


def reset_autoincrement(cursor):
    """Сбрасывает AUTOINCREMENT счетчики для очищенных таблиц."""
    print("\n[4/5] Сброс AUTOINCREMENT счетчиков...")
    
    tables_to_reset = [
        'orders', 'order_parts', 'order_services', 'order_comments',
        'order_status_history', 'order_visibility_history', 'order_symptoms',
        'order_appearance_tags', 'order_models', 'order_templates',
        'comment_attachments', 'tasks', 'task_checklists',
        'notifications', 'notification_preferences', 'customer_tokens', 'user_role_history',
        'payments', 'payment_receipts', 'cash_transactions', 'customer_wallet_transactions',
        'shop_sales', 'shop_sale_items', 'purchases', 'purchase_items', 'inventory',
        'inventory_items', 'suppliers', 'stock_movements', 'warehouse_logs',
        'action_logs', 'salary_accruals', 'salary_bonuses', 'salary_fines',
        'salary_payments',
        'order_statuses', 'services', 'devices', 'customers', 'device_types', 'device_brands',
        'masters', 'managers', 'symptoms', 'appearance_tags', 'parts', 'part_categories',
        'users',
    ]
    
    reset_count = 0
    for table in tables_to_reset:
        try:
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name = ?", (table,))
            if cursor.rowcount > 0:
                reset_count += 1
        except:
            pass
    
    print(f"      [OK] Сброшено {reset_count} счетчиков\n")


def main():
    """Основная функция очистки."""
    print("="*80)
    print("ОЧИСТКА БАЗЫ ДАННЫХ ОТ ТЕСТОВЫХ ДАННЫХ")
    print("="*80)
    
    # Проверяем существование БД
    if not os.path.exists(DB_PATH):
        print(f"[ОШИБКА] База данных не найдена: {DB_PATH}")
        return
    
    # Поддержка --yes флага
    auto_yes = '--yes' in sys.argv or '-y' in sys.argv
    
    if not auto_yes:
        print("\n[ВНИМАНИЕ!]")
        print("Этот скрипт удалит ВСЕ операционные данные, включая:")
        print("  - Заявки, оплаты, финансы, магазин, склад, закупки, логи, зарплата")
        print("  - Клиентов, устройства, типы и бренды устройств")
        print("  - Услуги, статусы заявок")
        print("  - Пользователей (кроме одного admin), мастеров, менеджеров")
        print("  - Симптомы, теги, товары и каталоги")
        print("\nОстанутся: настройки, статьи приходов/расходов, шаблоны печати и писем.")
        print("Будет создана резервная копия перед очисткой.")
        print("\nДля продолжения запустите с флагом --yes")
        return
    
    # Создаем резервную копию
    backup_path = create_backup()
    
    # Подключаемся к БД
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = OFF')  # Отключаем FK для быстрого удаления
    cursor = conn.cursor()
    
    # Показываем статистику ДО очистки
    print("\n[2/5] Статистика ДО очистки:")
    print("-" * 80)
    
    tables_to_delete = [
        'action_logs', 'order_status_history', 'order_visibility_history',
        'order_symptoms', 'order_appearance_tags', 'order_models',
        'customer_wallet_transactions', 'cash_transactions', 'payment_receipts',
        'payments', 'shop_sale_items', 'shop_sales', 'warehouse_logs',
        'stock_movements', 'inventory_items', 'inventory', 'purchase_items',
        'purchases', 'salary_accruals', 'salary_bonuses', 'salary_fines',
        'salary_payments', 'notifications', 'notification_preferences', 'customer_tokens', 'user_role_history',
        'task_checklists', 'tasks', 'comment_attachments', 'order_comments',
        'order_parts', 'order_services', 'orders', 'order_templates', 'suppliers',
        'order_statuses', 'services', 'devices', 'customers', 'device_types', 'device_brands',
        'masters', 'managers', 'symptoms', 'appearance_tags', 'parts', 'part_categories',
    ]
    
    before_total = show_statistics(cursor, "Таблицы к удалению", tables_to_delete)
    
    # Удаляем данные
    print("\n[3/5] Удаление данных...")
    print("-" * 80)
    
    # Порядок удаления: сначала зависимые (дочерние), потом основные
    delete_queries = [
        # Логи и история
        "DELETE FROM action_logs",
        "DELETE FROM order_status_history",
        "DELETE FROM order_visibility_history",
        "DELETE FROM order_symptoms",
        "DELETE FROM order_appearance_tags",
        "DELETE FROM order_models",
        # Уведомления и прочее операционное
        "DELETE FROM notifications",
        "DELETE FROM notification_preferences",
        "DELETE FROM customer_tokens",
        "DELETE FROM user_role_history",
        # Задачи (task_checklists -> tasks)
        "DELETE FROM task_checklists",
        "DELETE FROM tasks",
        # Финансы
        "DELETE FROM customer_wallet_transactions",
        "DELETE FROM cash_transactions",
        "DELETE FROM payment_receipts",
        "DELETE FROM payments",
        # Магазин
        "DELETE FROM shop_sale_items",
        "DELETE FROM shop_sales",
        # Склад
        "DELETE FROM warehouse_logs",
        "DELETE FROM stock_movements",
        "DELETE FROM inventory_items",
        "DELETE FROM inventory",
        "DELETE FROM purchase_items",
        "DELETE FROM purchases",
        # Зарплата
        "DELETE FROM salary_accruals",
        "DELETE FROM salary_bonuses",
        "DELETE FROM salary_fines",
        "DELETE FROM salary_payments",
        # Заявки: вложения комментариев до комментариев
        "DELETE FROM comment_attachments",
        "DELETE FROM order_comments",
        "DELETE FROM order_parts",
        "DELETE FROM order_services",
        "DELETE FROM order_templates",
        "DELETE FROM orders",
        "DELETE FROM suppliers",
        # Справочники и сущности (после заявок)
        "DELETE FROM order_statuses",
        "DELETE FROM services",
        "DELETE FROM devices",
        "DELETE FROM customers",
        "DELETE FROM device_types",
        "DELETE FROM device_brands",
        "DELETE FROM masters",
        "DELETE FROM managers",
        "DELETE FROM symptoms",
        "DELETE FROM appearance_tags",
        "DELETE FROM parts",
        "DELETE FROM part_categories",
    ]
    
    deleted_total = 0
    for query in delete_queries:
        try:
            table_name = query.split()[-1]
            before_count = get_table_count(cursor, table_name)
            cursor.execute(query)
            deleted = cursor.rowcount
            deleted_total += deleted
            if deleted > 0:
                print(f"  {table_name:<40} {deleted:>8} записей удалено")
        except Exception as e:
            print(f"  [ОШИБКА] {table_name}: {e}")
    
    print(f"\n  {'ИТОГО удалено':<40} {deleted_total:>8} записей")
    
    # Удаляем всех пользователей кроме одного админа
    cursor.execute("SELECT id FROM users WHERE role = 'admin' AND (is_active = 1 OR is_active IS NULL) ORDER BY id LIMIT 1")
    admin_row = cursor.fetchone()
    if admin_row:
        admin_id = admin_row[0]
        cursor.execute("DELETE FROM users WHERE id != ?", (admin_id,))
        users_deleted = cursor.rowcount
        if users_deleted > 0:
            print(f"  {'users (кроме admin)':<40} {users_deleted:>8} записей удалено")
        deleted_total += users_deleted
    else:
        print("  [ВНИМАНИЕ] Админ не найден, таблица users не трогается")
    
    # Сбрасываем AUTOINCREMENT
    reset_autoincrement(cursor)
    
    # Коммитим изменения
    conn.commit()
    
    # Показываем статистику ПОСЛЕ очистки
    print("\n[5/5] Статистика ПОСЛЕ очистки:")
    print("-" * 80)
    after_total = show_statistics(cursor, "Очищенные таблицы", tables_to_delete)
    
    # Показываем сохранённые таблицы (настройки, статьи, шаблоны)
    tables_to_keep = [
        'general_settings', 'system_settings', 'transaction_categories',
        'print_templates', 'permissions', 'role_permissions', 'schema_migrations', 'users',
    ]
    kept_total = show_statistics(cursor, "Сохранённые таблицы (настройки, статьи, шаблоны)", tables_to_keep)
    
    # Итоговая статистика
    print("\n" + "="*80)
    print("ИТОГОВАЯ СТАТИСТИКА:")
    print("="*80)
    print(f"  Удалено записей:     {before_total:>8}")
    print(f"  Осталось записей:    {after_total:>8}")
    print(f"  Сохранено записей:   {kept_total:>8}")
    print(f"  Резервная копия:     {backup_path}")
    print("="*80)
    
    conn.close()
    
    print("\n[OK] Очистка базы данных завершена успешно!")
    print(f"     Резервная копия сохранена: {backup_path}")


if __name__ == '__main__':
    main()
