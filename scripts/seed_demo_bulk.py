#!/usr/bin/env python3
"""
Массовое наполнение демо-БД (PostgreSQL): пользователи, клиенты, заявки, склад, закупки, продажи.

Запуск на сервере (из корня репозитория, с .env):
  export NIKA_DEMO_SEED_CONFIRM=YES
  python scripts/seed_demo_bulk.py --yes

Пароль для всех созданных учёток входа: Demo2026!
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import uuid
from datetime import datetime, timedelta
from io import StringIO

try:
    import psycopg2
    from psycopg2 import errors as pg_errors
    from psycopg2.extras import execute_batch
except ImportError:
    print("Нужен пакет psycopg2: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(1)

from werkzeug.security import generate_password_hash

CONFIRM_ENV = "NIKA_DEMO_SEED_CONFIRM"

MEME_FIRST = (
    "Линус Т.",
    "Ричард Столман (косплей)",
    "Дядя Боб",
    "Капитан Очевидность IT",
    "Сеньор-помидор",
    "Мидл-мемолог",
    "Джун без страховки",
    "DevOps с бубном",
    "SRE без сна",
    "Фронт на чувствах",
    "Бэкенд на кофеине",
    "Фулстек на молитве",
    "Тимлид «ещё поработаем»",
    "HR «мы семья»",
    "Стажёр rm -rf",
    "Инженер «у меня работает»",
    "QA «а вы точно деплоили?»",
    "Сисадмин «перезагрузи»",
    "Дата-инженер «NULL это фича»",
    "Безопасник «зачем вам root»",
)

MEME_LAST = (
    "Торвальдс",
    "Гейтс (не тот)",
    "Безос (курьер)",
    "Цукерберг (мета)",
    "Пейдж (поиск)",
    "Брин (поиск)",
    "Кармак",
    "Нормак",
    "Дормак",
    "Стековерфлоу",
    "Копипаста",
    "Регулярка",
    "YAML-отступ",
    "Docker Whale",
    "Kubernetes Pod",
    "Helm Chart",
    "Nginx 502",
    "Gunicorn Worker",
    "Postgres Vacuum",
)

MEME_COMMENTS = (
    "Клиент утверждает: «вчера всё работало».",
    "Симптом: синий экран моральный.",
    "Просят починить Wi‑Fi «настроение».",
    "Заявка: «компьютер шумит как биткоин-ферма».",
    "Пароль от устройства: 12345 (не сработал).",
    "It works on my machine™",
    "git push --force && уволиться",
    "sudo make me a sandwich",
    "Есть 2 проблемы: кэш и всё остальное.",
    "Отладка в проде — наш спринт.",
    "Мем: «это не баг, это undocumented feature».",
    "Просьба: «сделайте как у Apple, но бесплатно».",
    "Ноутбук после npm install не влезает в сумку.",
    "Телефон: чинить после падения с этажа самооценки.",
    "Планшет: разрядился пока искали зарядку.",
    "ПК: тормозит от количества вкладок Chrome.",
    "Монитор: горит от Excel на втором экране.",
    "Принтер: опять дух бутылки.",
)

MEME_APPEARANCE = (
    "корпус как после хакатона",
    "царапины боевые",
    "наклейка «Не трогать, прод»",
    "следы кофе и оптимизма",
    "вмятина «фича, не баг»",
)

MEME_DEVICES = (
    "Ноутбук «Дебаг-печенье»",
    "Смартфон «Пуш в мейн»",
    "Планшет «Спринт не влез»",
    "ПК «Рендерит мемы»",
    "Умные часы «тик-так tech debt»",
)

# Справочники: типы и бренды устройств (уникальное имя в БД)
CATALOG_DEVICE_TYPES = (
    "Смартфон",
    "Ноутбук",
    "Планшет",
    "ПК",
    "Умные часы",
    "Игровая приставка",
    "Монитор",
    "МФУ / принтер",
    "Роутер",
    "ИБП",
    "Наушники",
    "Носимый гаджет",
)
CATALOG_DEVICE_BRANDS = (
    "Apple",
    "Samsung",
    "Xiaomi",
    "Google",
    "OnePlus",
    "ASUS",
    "Lenovo",
    "Dell",
    "HP",
    "MSI",
    "Acer",
    "Huawei",
    "Honor",
    "Sony",
    "LG",
)

DEMO_SYMPTOMS = (
    "Не включается после обновления",
    "Перегрев при открытии Jira",
    "Разряжается за один stand-up",
    "Нет сети, «а у соседа работает»",
    "Глючит тач после кофе",
    "Шумит как сервер в датацентре",
    "Синий экран на совести Windows",
    "Просит пароль, который «точно верный»",
    "Камера не фокусируется на багах",
    "Микрофон ловит только эхо-камеру",
    "USB не видит флешку с бэкапом",
    "Wi‑Fi отваливается на ретро",
    "Bluetooth ищет наушники вечность",
    "Динамик хрипит на мемах",
    "Кнопка питания «настроение»",
    "После падения не включается экран",
    "Вода / жидкость (энергетик)",
    "Не заряжается от «родной» зарядки",
    "Быстро разряжается в холоде",
    "Тормозит на 100 вкладках",
)

DEMO_APPEARANCE_TAGS = (
    "Корпус: царапины",
    "Корпус: сколы",
    "Экран: трещина",
    "Экран: без трещин",
    "Потёртости клавиатуры",
    "Вмятина на крышке",
    "Следы вскрытия",
    "Наклейки сервисные",
    "Комплект: без коробки",
    "Комплект: зарядка в комплекте",
    "Статус: после другого СЦ",
)

# Ключ в part_categories -> строка категории для запчастей (часть поля parts.category)
PART_CATEGORY_KEYS = (
    "Экраны и тачскрины",
    "Аккумуляторы",
    "Шлейфы и разъёмы",
    "Клавиатуры",
    "Корпусные детали",
    "Инструменты",
    "Расходники",
    "Кабели и зарядки",
)
PART_CATEGORY_FOR_STOCK = (
    "Экраны и тачскрины",
    "Аккумуляторы",
    "Шлейфы и разъёмы",
    "Клавиатуры",
    "Корпусные детали",
    "Расходники",
)

DELETE_ORDER = [
    "DELETE FROM payment_receipts",
    "DELETE FROM payments",
    "DELETE FROM cash_transactions",
    "DELETE FROM salary_accruals",
    "DELETE FROM salary_bonuses",
    "DELETE FROM salary_fines",
    "DELETE FROM salary_payments",
    "DELETE FROM task_checklists",
    "DELETE FROM tasks",
    "DELETE FROM order_appearance_tags",
    "DELETE FROM comment_attachments",
    "DELETE FROM order_comments",
    "DELETE FROM order_parts",
    "DELETE FROM order_services",
    "DELETE FROM order_status_history",
    "DELETE FROM order_symptoms",
    "DELETE FROM order_visibility_history",
    "DELETE FROM orders",
    "DELETE FROM order_models",
    "DELETE FROM shop_sale_items",
    "DELETE FROM shop_sales",
    "DELETE FROM purchase_items",
    "DELETE FROM purchases",
    "DELETE FROM suppliers",
    "DELETE FROM stock_movements",
    "DELETE FROM warehouse_logs",
    "DELETE FROM inventory_items",
    "DELETE FROM inventory",
    "DELETE FROM parts",
    "DELETE FROM devices",
    "DELETE FROM customer_wallet_transactions",
    "DELETE FROM customer_tokens",
    "DELETE FROM customers",
    "DELETE FROM notifications",
    "DELETE FROM notification_preferences",
    "DELETE FROM action_logs",
    "DELETE FROM managers",
    "DELETE FROM masters",
    "DELETE FROM staff_chat_reactions",
    "DELETE FROM staff_chat_attachments",
    "DELETE FROM staff_chat_read_cursors",
    "DELETE FROM staff_chat_web_push_subscriptions",
    "DELETE FROM staff_chat_messages",
    "DELETE FROM users",
]


def _safe_execute(cur, sql: str) -> None:
    try:
        cur.execute(sql)
    except pg_errors.UndefinedTable:
        pass


def wipe(cur) -> None:
    for stmt in DELETE_ORDER:
        _safe_execute(cur, stmt)


def ensure_device_types_and_brands(cur) -> tuple[list[int], list[int]]:
    """Гарантирует строки справочников device_types / device_brands и возвращает списки id."""
    type_ids: list[int] = []
    for i, name in enumerate(CATALOG_DEVICE_TYPES):
        cur.execute(
            """
            INSERT INTO device_types (name, sort_order)
            VALUES (%s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (name, i),
        )
        cur.execute("SELECT id FROM device_types WHERE name = %s", (name,))
        type_ids.append(int(cur.fetchone()[0]))
    brand_ids: list[int] = []
    for i, name in enumerate(CATALOG_DEVICE_BRANDS):
        cur.execute(
            """
            INSERT INTO device_brands (name, sort_order)
            VALUES (%s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (name, i),
        )
        cur.execute("SELECT id FROM device_brands WHERE name = %s", (name,))
        brand_ids.append(int(cur.fetchone()[0]))
    return type_ids, brand_ids


def seed_order_models(cur) -> list[tuple[int, str]]:
    """После wipe таблица order_models пуста — заполняем связку «бренд + тип» для model_id."""
    combos: list[str] = []
    for b in CATALOG_DEVICE_BRANDS:
        for t in CATALOG_DEVICE_TYPES:
            combos.append(f"{b} {t} (демо)")
    random.shuffle(combos)
    out: list[tuple[int, str]] = []
    for name in combos[: min(96, len(combos))]:
        cur.execute("INSERT INTO order_models (name) VALUES (%s) RETURNING id", (name,))
        mid = int(cur.fetchone()[0])
        out.append((mid, name))
    return out


def ensure_symptoms(cur) -> list[int]:
    ids: list[int] = []
    for i, name in enumerate(DEMO_SYMPTOMS):
        cur.execute(
            """
            INSERT INTO symptoms (name, sort_order)
            VALUES (%s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (name, i),
        )
        cur.execute("SELECT id FROM symptoms WHERE name = %s", (name,))
        ids.append(int(cur.fetchone()[0]))
    return ids


def ensure_appearance_tags(cur) -> list[int]:
    ids: list[int] = []
    for i, name in enumerate(DEMO_APPEARANCE_TAGS):
        cur.execute(
            """
            INSERT INTO appearance_tags (name, sort_order)
            VALUES (%s, %s)
            ON CONFLICT (name) DO NOTHING
            """,
            (name, i),
        )
        cur.execute("SELECT id FROM appearance_tags WHERE name = %s", (name,))
        ids.append(int(cur.fetchone()[0]))
    return ids


def ensure_part_categories_map(cur) -> dict[str, int]:
    m: dict[str, int] = {}
    for name in PART_CATEGORY_KEYS:
        cur.execute("SELECT id FROM part_categories WHERE name = %s", (name,))
        r = cur.fetchone()
        if r:
            m[name] = int(r[0])
        else:
            cur.execute("INSERT INTO part_categories (name) VALUES (%s) RETURNING id", (name,))
            m[name] = int(cur.fetchone()[0])
    return m


def seed_suppliers(cur, n: int = 24) -> list[int]:
    ids: list[int] = []
    for i in range(n):
        nm = f"ООО «Поставка #{i + 1:02d} — {MEME_LAST[i % len(MEME_LAST)]}»"
        cur.execute(
            """
            INSERT INTO suppliers (name, contact_person, phone, email, is_active)
            VALUES (%s, %s, %s, %s, 1)
            RETURNING id
            """,
            (nm, f"Менеджер #{i}", f"7495{1000000 + i:07d}", f"supply{i}@demo.supplier.invalid"),
        )
        ids.append(int(cur.fetchone()[0]))
    return ids


def ensure_order_statuses(cur) -> list[int]:
    cur.execute("SELECT id FROM order_statuses WHERE COALESCE(is_archived,0)=0 ORDER BY sort_order, id")
    ids = [row[0] for row in cur.fetchall()]
    if ids:
        return [int(x) for x in ids]
    cur.execute(
        """
        INSERT INTO order_statuses (code, name, color, sort_order, is_default)
        VALUES
          ('new', 'Новая', '#6c757d', 1, 1),
          ('diag', 'Диагностика', '#17a2b8', 2, 0),
          ('repair', 'В ремонте', '#ffc107', 3, 0),
          ('ready', 'Готово', '#28a745', 4, 0),
          ('closed', 'Выдано', '#343a40', 5, 0)
        RETURNING id
        """
    )
    return [int(row[0]) for row in cur.fetchall()]


def ensure_services(cur) -> list[int]:
    cur.execute("SELECT id FROM services ORDER BY id LIMIT 20")
    ids = [int(row[0]) for row in cur.fetchall()]
    if ids:
        return ids
    names = ("Диагностика мемов", "Чистка от пыли и legacy", "Замена термопасты на шутки", "Настройка Wi‑Fi души", "Восстановление данных после npm")
    for n in names:
        cur.execute(
            "INSERT INTO services (name, price, is_default, sort_order) VALUES (%s, %s, 0, 0) RETURNING id",
            (n, random.randint(500, 5000)),
        )
        ids.append(cur.fetchone()[0])
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description="Демо-сидер PostgreSQL (разрушительный для текущих данных).")
    ap.add_argument("--yes", action="store_true", help="Подтвердить очистку таблиц")
    ap.add_argument("--orders", type=int, default=10_000, help="Количество заявок")
    ap.add_argument("--customers", type=int, default=5_000, help="Количество клиентов")
    ap.add_argument("--staff-users", type=int, default=10_000, help="Всего учёток входа (именованные + добивка)")
    ap.add_argument("--parts", type=int, default=400, help="Позиций на складе")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    args = ap.parse_args()
    random.seed(args.seed)

    if not args.yes:
        print("Укажите --yes и установите NIKA_DEMO_SEED_CONFIRM=YES", file=sys.stderr)
        return 2
    if os.environ.get(CONFIRM_ENV, "").strip().upper() != "YES":
        print(f"Установите {CONFIRM_ENV}=YES для защиты от случайного запуска.", file=sys.stderr)
        return 2

    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn.startswith("postgres"):
        print("Ожидается PostgreSQL DATABASE_URL в окружении.", file=sys.stderr)
        return 2

    pwd_hash = generate_password_hash("Demo2026!")
    n_orders = max(100, min(args.orders, 200_000))
    n_customers = max(50, min(args.customers, 100_000))
    n_staff = max(10, min(args.staff_users, 50_000))
    n_parts = max(20, min(args.parts, 5000))

    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        wipe(cur)

        type_ids, brand_ids = ensure_device_types_and_brands(cur)
        model_rows = seed_order_models(cur)
        symptom_ids = ensure_symptoms(cur)
        appearance_tag_ids = ensure_appearance_tags(cur)
        part_cat_map = ensure_part_categories_map(cur)
        supplier_ids = seed_suppliers(cur)

        status_ids = ensure_order_statuses(cur)
        service_ids = ensure_services(cur)

        # Учётки входа: demo_admin + именованные + bench_* до n_staff
        roles_cycle = ["manager", "master", "viewer", "viewer"]
        staff_rows: list[tuple[str, str, str, str]] = [("demo_admin", pwd_hash, "admin", "Демо-админ")]
        used = {"demo_admin"}

        for i in range(80):
            if len(staff_rows) >= n_staff:
                break
            fn = MEME_FIRST[i % len(MEME_FIRST)]
            ln = MEME_LAST[i % len(MEME_LAST)]
            base = f"demo_{fn[:5]}_{ln[:5]}_{i}".lower()
            uname = "".join(c if c.isalnum() or c == "_" else "_" for c in base)[:40]
            u = uname
            k = 0
            while u in used:
                k += 1
                u = f"{uname[:34]}_{k}"
            used.add(u)
            role = roles_cycle[i % len(roles_cycle)]
            staff_rows.append((u, pwd_hash, role, f"{fn} {ln}"))

        bench_i = 0
        while len(staff_rows) < n_staff:
            u = f"bench_u_{bench_i:05d}"
            bench_i += 1
            if u in used:
                continue
            used.add(u)
            staff_rows.append((u, pwd_hash, "viewer", f"Мем-наблюдатель #{bench_i}"))

        execute_batch(
            cur,
            """
            INSERT INTO users (username, password_hash, role, display_name, is_active)
            VALUES (%s, %s, %s, %s, 1)
            """,
            staff_rows,
            page_size=500,
        )

        cur.execute("SELECT id, role FROM users ORDER BY id")
        user_by_role: dict[str, list[int]] = {}
        all_uids = []
        for uid, role in cur.fetchall():
            all_uids.append(int(uid))
            user_by_role.setdefault(str(role), []).append(int(uid))

        mgr_ids: list[int] = []
        for i in range(12):
            cur.execute(
                "INSERT INTO managers (name, active) VALUES (%s, 1) RETURNING id",
                (f"Менеджер {MEME_LAST[i % len(MEME_LAST)]}",),
            )
            mgr_ids.append(cur.fetchone()[0])

        mst_ids: list[int] = []
        for i in range(12):
            cur.execute(
                "INSERT INTO masters (name, active) VALUES (%s, 1) RETURNING id",
                (f"Мастер {MEME_FIRST[i % len(MEME_FIRST)]}",),
            )
            mst_ids.append(cur.fetchone()[0])

        part_buf = StringIO()
        for p in range(1, n_parts + 1):
            name = f"Запчасть-мем #{p}"
            sku = f"DEMO-{p:05d}"
            cat_key = random.choice(PART_CATEGORY_FOR_STOCK)
            cat_label = cat_key.split()[0]
            cid = part_cat_map[cat_key]
            buy = round(random.uniform(100, 8000), 2)
            sell = round(buy * random.uniform(1.15, 1.8), 2)
            stock = random.randint(0, 500)
            line = (
                f"{name}\t{sku}\tМем-категория: {cat_key}\t{sell}\t{buy}\t{stock}\t5\t{cat_label}\t"
                f"Поставщик npm registry\tшт\t30\t0\t{cid}\t\n"
            )
            part_buf.write(line)
        part_buf.seek(0)
        cur.copy_expert(
            """
            COPY parts (name, part_number, description, price, purchase_price, stock_quantity,
              min_quantity, category, supplier, unit, warranty_days, is_deleted, category_id, comment)
            FROM STDIN WITH (FORMAT text, NULL '')
            """,
            part_buf,
        )

        cur.execute("SELECT id FROM parts ORDER BY id")
        part_ids = [int(r[0]) for r in cur.fetchall()]

        cust_buf = StringIO()
        for c in range(1, n_customers + 1):
            name = f"{random.choice(MEME_FIRST)} {random.choice(MEME_LAST)} #{c}"
            phone = str(79_990_000_000 + c)
            if len(phone) != 11:
                phone = f"7999{(c % 10_000_000):07d}"
            mail = f"demo_client_{c}@example.invalid"
            cust_buf.write(f"{name}\t{phone}\t{mail}\n")
        cust_buf.seek(0)
        cur.copy_expert(
            "COPY customers (name, phone, email) FROM STDIN WITH (FORMAT text, NULL '')",
            cust_buf,
        )

        cur.execute("SELECT id FROM customers ORDER BY id")
        customer_ids = [int(r[0]) for r in cur.fetchall()]

        dev_buf = StringIO()
        for d in range(1, n_orders + 1):
            cid = customer_ids[(d - 1) % len(customer_ids)]
            dt = type_ids[(d - 1) % len(type_ids)]
            db = brand_ids[(d * 3 + 7) % len(brand_ids)]
            serial = f"SN-MEME-{d:08d}"
            sym = random.choice(MEME_COMMENTS)[:200]
            app = random.choice(MEME_APPEARANCE)[:200]
            dev_buf.write(f"{cid}\t{dt}\t{db}\t{serial}\t\t{sym}\t{app}\t\n")
        dev_buf.seek(0)
        cur.copy_expert(
            "COPY devices (customer_id, device_type_id, device_brand_id, serial_number, password, symptom_tags, appearance_tags, comment) "
            "FROM STDIN WITH (FORMAT text, NULL '')",
            dev_buf,
        )

        cur.execute("SELECT id FROM devices ORDER BY id")
        device_ids = [int(r[0]) for r in cur.fetchall()]

        start = datetime.now() - timedelta(days=400)
        ord_buf = StringIO()
        for i in range(1, n_orders + 1):
            oid = str(uuid.uuid4())
            dev_id = device_ids[i - 1]
            cid = customer_ids[(i - 1) % len(customer_ids)]
            mgr = random.choice(mgr_ids)
            mst = str(random.choice(mst_ids)) if random.random() > 0.15 else ""
            st = random.choice(status_ids)
            prep_c = random.choice([0, 0, 50000, 120000, 30000])
            prep_t = str(prep_c // 100) if prep_c else "0"
            when = start + timedelta(seconds=random.randint(0, 400 * 86400))
            ca = when.strftime("%Y-%m-%d %H:%M:%S")
            ua = ca
            comment = random.choice(MEME_COMMENTS).replace("\t", " ")
            mid, mname = model_rows[(i - 1) % len(model_rows)]
            hidden = "0"
            is_del = "0"
            line = "\t".join(
                [
                    oid,
                    str(dev_id),
                    str(cid),
                    str(mgr),
                    mst,
                    "new",
                    prep_t,
                    "",
                    random.choice(MEME_APPEARANCE)[:120],
                    comment[:500],
                    ca,
                    ua,
                    "мем-тег",
                    "",
                    str(st),
                    hidden,
                    mname[:120],
                    str(mid),
                    str(prep_c),
                    is_del,
                    "",
                    "",
                    "",
                ]
            )
            ord_buf.write(line + "\n")
        ord_buf.seek(0)
        cur.copy_expert(
            """
            COPY orders (order_id, device_id, customer_id, manager_id, master_id, status, prepayment,
              password, appearance, comment, created_at, updated_at, symptom_tags, intake_checklist,
              status_id, hidden, model, model_id, prepayment_cents, is_deleted, deleted_at, deleted_by_id, deleted_reason)
            FROM STDIN WITH (FORMAT text, NULL '')
            """,
            ord_buf,
        )

        cur.execute("SELECT id FROM orders ORDER BY id")
        order_pk = [int(r[0]) for r in cur.fetchall()]

        osym_rows: list[tuple[int, int]] = []
        seen_os: set[tuple[int, int]] = set()
        for pk in order_pk:
            k = random.randint(1, min(3, len(symptom_ids)))
            for sid in random.sample(symptom_ids, k=k):
                key = (pk, sid)
                if key not in seen_os:
                    seen_os.add(key)
                    osym_rows.append(key)
        execute_batch(
            cur,
            "INSERT INTO order_symptoms (order_id, symptom_id) VALUES (%s, %s)",
            osym_rows,
            page_size=800,
        )

        oat_rows: list[tuple[int, int]] = []
        seen_oa: set[tuple[int, int]] = set()
        for pk in order_pk:
            k = random.randint(1, min(2, len(appearance_tag_ids)))
            for aid in random.sample(appearance_tag_ids, k=k):
                key = (pk, aid)
                if key not in seen_oa:
                    seen_oa.add(key)
                    oat_rows.append(key)
        execute_batch(
            cur,
            "INSERT INTO order_appearance_tags (order_id, appearance_tag_id) VALUES (%s, %s)",
            oat_rows,
            page_size=800,
        )

        pay_rows = []
        admin_ids = user_by_role.get("admin") or all_uids[:3]
        for pk in random.sample(order_pk, k=min(len(order_pk), len(order_pk) // 4)):
            pay_rows.append(
                (
                    pk,
                    round(random.uniform(500, 15000), 2),
                    random.choice(("cash", "card", "transfer")),
                    random.choice(admin_ids),
                    "demo_seed",
                    "оплата мем-услуг",
                )
            )
        execute_batch(
            cur,
            """
            INSERT INTO payments (order_id, amount, payment_type, created_by, created_by_username, comment)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            pay_rows,
            page_size=500,
        )

        op_rows = []
        for pk in random.sample(order_pk, k=min(len(order_pk), len(order_pk) // 5)):
            pid = random.choice(part_ids)
            op_rows.append(
                (
                    pk,
                    pid,
                    f"Позиция мем #{pid}",
                    random.randint(1, 3),
                    round(random.uniform(300, 9000), 2),
                    round(random.uniform(100, 3000), 2),
                )
            )
        execute_batch(
            cur,
            """
            INSERT INTO order_parts (order_id, part_id, name, quantity, price, purchase_price)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            op_rows,
            page_size=500,
        )

        svc_seed_rows: list[tuple[int, int, str, int, float]] = []
        for pk in random.sample(order_pk, k=min(len(order_pk), max(3500, len(order_pk) // 3))):
            sv = random.choice(service_ids)
            cur.execute("SELECT name, price FROM services WHERE id = %s", (sv,))
            sn, sp = cur.fetchone()
            svc_seed_rows.append((pk, int(sv), str(sn), 1, float(sp)))
        execute_batch(
            cur,
            """
            INSERT INTO order_services (order_id, service_id, name, quantity, price)
            VALUES (%s, %s, %s, %s, %s)
            """,
            svc_seed_rows,
            page_size=500,
        )

        pur_ids: list[int] = []
        uid0 = admin_ids[0]
        for p in range(800):
            sup_id = random.choice(supplier_ids)
            cur.execute("SELECT name FROM suppliers WHERE id = %s", (sup_id,))
            sup_name = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO purchases (supplier_id, supplier_name, purchase_date, total_amount, status, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    sup_id,
                    sup_name,
                    datetime.now() - timedelta(days=random.randint(1, 300)),
                    0,
                    random.choice(("completed", "draft", "completed")),
                    random.choice(MEME_COMMENTS)[:200],
                    uid0,
                ),
            )
            pur_ids.append(cur.fetchone()[0])

        mov_batch = []
        for pr in pur_ids:
            for _ in range(random.randint(1, 4)):
                pid = random.choice(part_ids)
                qty = random.randint(5, 200)
                pprice = round(random.uniform(50, 2000), 2)
                tprice = round(qty * pprice, 2)
                cur.execute(
                    """
                    INSERT INTO purchase_items (purchase_id, part_id, quantity, purchase_price, total_price)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (pr, pid, qty, pprice, tprice),
                )
                mov_batch.append((pid, "purchase", qty, pr, "purchase", uid0, "закупка мем-деталей"))

        for _ in range(6000):
            pid = random.choice(part_ids)
            qty = -random.randint(1, 15)
            mov_batch.append((pid, "sale", qty, random.choice(order_pk), "order", uid0, "расход на заявку"))

        execute_batch(
            cur,
            """
            INSERT INTO stock_movements (part_id, movement_type, quantity, reference_id, reference_type, created_by, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            mov_batch,
            page_size=800,
        )

        sale_ids: list[int] = []
        for s in range(2500):
            cid = random.choice(customer_ids)
            cur.execute(
                """
                INSERT INTO shop_sales (customer_id, customer_name, customer_phone, manager_id, master_id,
                  total_amount, discount, final_amount, paid_amount, payment_method, comment, sale_date, created_by_id, created_by_username)
                SELECT %s, c.name, c.phone, %s, %s, 0, 0, 0, 0, %s, %s, %s, %s, %s
                FROM customers c WHERE c.id = %s
                RETURNING id
                """,
                (
                    cid,
                    random.choice(mgr_ids),
                    random.choice(mst_ids),
                    random.choice(("cash", "card")),
                    random.choice(MEME_COMMENTS)[:200],
                    datetime.now() - timedelta(days=random.randint(1, 200)),
                    uid0,
                    "demo_seed",
                    cid,
                ),
            )
            sale_ids.append(cur.fetchone()[0])

        sit_rows = []
        for sid in sale_ids:
            if random.random() < 0.55 and service_ids:
                sv = random.choice(service_ids)
                cur.execute("SELECT name, price FROM services WHERE id = %s", (sv,))
                sn, sp = cur.fetchone()
                q = 1
                price = float(sp)
                tot = price * q
                sit_rows.append((sid, "service", sv, sn, None, None, None, q, price, 0, tot))
            if random.random() < 0.65:
                pid = random.choice(part_ids)
                cur.execute("SELECT name, part_number, price, purchase_price FROM parts WHERE id = %s", (pid,))
                row = cur.fetchone()
                pn, sku, price, pp = row[0], row[1], float(row[2]), float(row[3] or 0)
                q = random.randint(1, 5)
                tot = price * q
                sit_rows.append((sid, "part", None, None, pid, pn, sku or "", q, price, pp, tot))

        execute_batch(
            cur,
            """
            INSERT INTO shop_sale_items (shop_sale_id, item_type, service_id, service_name, part_id, part_name, part_sku,
              quantity, price, purchase_price, total)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            sit_rows,
            page_size=600,
        )

        for sid in sale_ids:
            cur.execute("SELECT COALESCE(SUM(total),0) FROM shop_sale_items WHERE shop_sale_id = %s", (sid,))
            tot = float(cur.fetchone()[0])
            cur.execute(
                """
                UPDATE shop_sales SET total_amount = %s, final_amount = %s, paid_amount = %s WHERE id = %s
                """,
                (tot, tot * random.choice((1.0, 1.0, 0.95)), tot * random.choice((1.0, 0.5, 1.0)), sid),
            )

        for pr in pur_ids:
            cur.execute(
                "UPDATE purchases SET total_amount = COALESCE((SELECT SUM(total_price) FROM purchase_items WHERE purchase_id = %s),0) WHERE id = %s",
                (pr, pr),
            )

        inv_ids: list[int] = []
        for inv in range(40):
            cur.execute(
                """
                INSERT INTO inventory (name, inventory_date, status, notes, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    f"Инвентаризация мемов #{inv+1}",
                    datetime.now() - timedelta(days=inv * 7),
                    random.choice(("completed", "draft")),
                    random.choice(MEME_COMMENTS)[:120],
                    uid0,
                ),
            )
            inv_ids.append(cur.fetchone()[0])

        ii_rows = []
        for iid in inv_ids:
            for pid in random.sample(part_ids, k=min(80, len(part_ids))):
                sq = random.randint(0, 300)
                aq = max(0, sq + random.randint(-5, 5))
                ii_rows.append((iid, pid, sq, aq, aq - sq, "мем-пересчёт"))
        execute_batch(
            cur,
            """
            INSERT INTO inventory_items (inventory_id, part_id, stock_quantity, actual_quantity, difference, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            ii_rows,
            page_size=800,
        )

        conn.commit()
        print("OK: демо-данные загружены.")
        print(f"  Учётки входа: {len(staff_rows)} (логин пример: demo_admin, bench_u_00050, …)")
        print("  Пароль для всех: Demo2026!")
        print(f"  Клиенты: {n_customers}, заявки: {n_orders}, запчасти: {n_parts}")
        print(
            f"  Справочники: типов {len(type_ids)}, брендов {len(brand_ids)}, моделей {len(model_rows)}, "
            f"симптомов {len(symptom_ids)}, тегов внешнего вида {len(appearance_tag_ids)}, "
            f"категорий запчастей {len(part_cat_map)}, поставщиков {len(supplier_ids)}"
        )
        return 0
    except Exception as e:
        conn.rollback()
        print(f"Ошибка: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
