"""
Миграция 020: Поставщики и Инвентаризация
- Таблица suppliers (поставщики)
- Таблица inventory (инвентаризационные ведомости)
- Таблица inventory_items (позиции инвентаризации)
- Обновление purchases для связи с suppliers
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up() -> None:
    """Применение миграции."""
    logger.info("Применение миграции 020: Поставщики и Инвентаризация")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Таблица suppliers (поставщики)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                inn TEXT,
                comment TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_suppliers_name ON suppliers(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_suppliers_is_active ON suppliers(is_active)')
        
        # 2. Обновление purchases: добавление связи с suppliers
        # Проверяем, существует ли уже supplier_id
        cursor.execute("PRAGMA table_info(purchases)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'supplier_id' not in columns:
            cursor.execute('ALTER TABLE purchases ADD COLUMN supplier_id INTEGER')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_purchases_supplier_id_new ON purchases(supplier_id)')
        
        # Обновляем существующие записи: создаем поставщиков из supplier_name
        cursor.execute('SELECT DISTINCT supplier_name FROM purchases WHERE supplier_name IS NOT NULL AND supplier_name != ""')
        existing_suppliers = cursor.fetchall()
        
        for (supplier_name,) in existing_suppliers:
            if supplier_name:
                # Проверяем, существует ли уже такой поставщик
                cursor.execute('SELECT id FROM suppliers WHERE name = ?', (supplier_name,))
                existing = cursor.fetchone()
                
                if not existing:
                    # Создаем нового поставщика
                    cursor.execute('''
                        INSERT INTO suppliers (name, is_active)
                        VALUES (?, 1)
                    ''', (supplier_name,))
                    supplier_id = cursor.lastrowid
                else:
                    supplier_id = existing[0]
                
                # Обновляем purchases для связи с поставщиком
                cursor.execute('''
                    UPDATE purchases 
                    SET supplier_id = ?
                    WHERE supplier_name = ? AND supplier_id IS NULL
                ''', (supplier_id, supplier_name))
        
        # 3. Таблица inventory (инвентаризационные ведомости)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                inventory_date DATE NOT NULL DEFAULT (DATE('now')),
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'completed', 'cancelled')),
                notes TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_date ON inventory(inventory_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(status)')
        
        # 4. Таблица inventory_items (позиции инвентаризации)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventory_id INTEGER NOT NULL,
                part_id INTEGER NOT NULL,
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                actual_quantity INTEGER NOT NULL DEFAULT 0,
                difference INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inventory_id) REFERENCES inventory(id) ON DELETE CASCADE,
                FOREIGN KEY (part_id) REFERENCES parts(id)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_items_inventory_id ON inventory_items(inventory_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inventory_items_part_id ON inventory_items(part_id)')
        
        conn.commit()
        logger.info("Миграция 020: Поставщики и Инвентаризация применена успешно")


def down() -> None:
    """Откат миграции."""
    logger.info("Откат миграции 020: Поставщики и Инвентаризация")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('DROP TABLE IF EXISTS inventory_items')
        cursor.execute('DROP TABLE IF EXISTS inventory')
        
        # Не удаляем suppliers, так как могут быть ссылки из purchases
        # Просто удаляем индекс, если нужно
        try:
            cursor.execute('DROP INDEX IF EXISTS idx_purchases_supplier_id_new')
        except Exception:
            pass
        
        conn.commit()
        logger.info("Миграция 020: Поставщики и Инвентаризация откачена")

