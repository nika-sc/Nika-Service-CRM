"""PostgreSQL CRM must not keep SQLite datetime() in SQL strings."""
import re
from pathlib import Path

_SQLITE_DATETIME = re.compile(
    r"(?<![\w])datetime\(\s*'now'|(?<![\w])datetime\(\s*created_at\s*\)"
)


def test_app_sql_has_no_sqlite_datetime():
    root = Path(__file__).resolve().parents[1] / "app"
    hits = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if _SQLITE_DATETIME.search(text):
            hits.append(str(path.relative_to(root.parent)))
    assert hits == []
