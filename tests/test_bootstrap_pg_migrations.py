"""OSS bootstrap dump must list every postgres_versions file in schema_migrations_pg."""
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
