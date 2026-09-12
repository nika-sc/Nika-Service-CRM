"""OSS bootstrap dump must list every postgres_versions file in schema_migrations_pg."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = ROOT / "app" / "database" / "migrations" / "postgres_versions"
DUMP = ROOT / "database" / "bootstrap" / "nikacrm_public_sanitized.sql"


def _expected_versions():
    rows = []
    for path in sorted(VERSIONS_DIR.glob("*.sql")):
        version, name = path.stem.split("_", 1)
        rows.append((version, name))
    return rows


def test_bootstrap_copy_lists_every_postgres_version():
    expected = _expected_versions()
    assert expected, "postgres_versions is empty"
    dump = DUMP.read_text(encoding="utf-8")
    marker = "COPY public.schema_migrations_pg"
    start = dump.index(marker)
    end = dump.index("\\.\n", start)
    block = dump[start:end]
    missing = [
        f"{version}_{name}"
        for version, name in expected
        if f"{version}\t{name}\t" not in block
    ]
    assert missing == [], f"schema_migrations_pg COPY missing: {missing}"


def test_bootstrap_readme_mentions_tip_version():
    tip = _expected_versions()[-1][0]
    readme = (ROOT / "database" / "bootstrap" / "README.md").read_text(encoding="utf-8")
    assert tip in readme


def _copy_rows(dump: str, table: str) -> list[str]:
    marker = f"COPY public.{table} "
    start = dump.index(marker)
    end = dump.index("\\.\n", start)
    body = dump[start:end].split("\n", 1)[1]
    return [line for line in body.splitlines() if line]


def test_bootstrap_ships_demo_catalog_not_owner_data():
    dump = DUMP.read_text(encoding="utf-8")
    types = _copy_rows(dump, "device_types")
    brands = _copy_rows(dump, "device_brands")
    models = _copy_rows(dump, "order_models")
    symptoms = _copy_rows(dump, "symptoms")
    appearance = _copy_rows(dump, "appearance_tags")
    parts = _copy_rows(dump, "parts")
    categories = _copy_rows(dump, "part_categories")
    customers = _copy_rows(dump, "customers")
    orders = _copy_rows(dump, "orders")

    assert 8 <= len(types) <= 40
    assert 10 <= len(brands) <= 60
    assert 20 <= len(models) <= 80
    assert 10 <= len(symptoms) <= 60
    assert 8 <= len(appearance) <= 40
    assert customers == []
    assert orders == []
    assert len(parts) == 1
    assert len(categories) == 1
    assert "Тестовый товар" in parts[0]
    assert "TEST-001" in parts[0]
    assert "Тестовая категория" in categories[0]
    assert "nika-sc.ru" not in dump

    junk = []
    for table, rows in (
        ("device_types", types),
        ("device_brands", brands),
        ("order_models", models),
        ("symptoms", symptoms),
        ("appearance_tags", appearance),
    ):
        for row in rows:
            name = row.split("\t")[1]
            stripped = name.strip()
            if stripped in {"-", "--", "---", "+", "=", "ХЗ"} or not re.search(
                r"[A-Za-zА-Яа-я0-9]", stripped
            ):
                junk.append(f"{table}:{name}")
    assert junk == []


def test_catalog_models_stay_complete_when_type_or_brand_is_chosen():
    src = (ROOT / "app" / "services" / "reference_service.py").read_text(encoding="utf-8")
    block = src.split("def get_catalog_models")[1].split("\n    def ")[0]
    assert "список всегда полный" in block
    assert "ORDER BY relevant DESC" in block
    assert "WHERE d.device_type_id = ?" not in block
