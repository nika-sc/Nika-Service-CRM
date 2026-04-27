"""Управление соединениями с БД (SQLite/PostgreSQL)."""
import logging
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Iterable, Optional, Sequence, Tuple

from app.config import Config

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import ThreadedConnectionPool
except Exception:  # pragma: no cover
    psycopg2 = None
    RealDictCursor = None
    ThreadedConnectionPool = None

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 0.1
LOCK_TIMEOUT = 20.0
_PG_POOL = None
_PG_POOL_DSN = None


def _get_database_path() -> str:
    return os.environ.get("DATABASE_PATH", Config.DATABASE_PATH)


def _get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "")


def _get_db_driver() -> str:
    driver = os.environ.get("DB_DRIVER", "").strip().lower()
    if driver in ("sqlite", "postgres"):
        return driver
    return "postgres" if _get_database_url().startswith("postgres") else "sqlite"


def _get_log_slow_queries() -> bool:
    return os.environ.get("LOG_SLOW_QUERIES", str(getattr(Config, "LOG_SLOW_QUERIES", True))).lower() == "true"


def _get_slow_query_threshold_ms() -> int:
    try:
        return int(os.environ.get("SLOW_QUERY_THRESHOLD_MS", str(getattr(Config, "SLOW_QUERY_THRESHOLD_MS", 150))))
    except Exception:
        return 150


def _get_pg_pool_minconn() -> int:
    try:
        return max(1, int(os.environ.get("PG_POOL_MINCONN", "2")))
    except Exception:
        return 2


def _get_pg_pool_maxconn() -> int:
    try:
        return max(_get_pg_pool_minconn(), int(os.environ.get("PG_POOL_MAXCONN", "20")))
    except Exception:
        return 20


def _get_pg_pool(database_url: str):
    global _PG_POOL, _PG_POOL_DSN
    if ThreadedConnectionPool is None:
        return None
    if _PG_POOL is not None and _PG_POOL_DSN == database_url:
        return _PG_POOL
    if _PG_POOL is not None:
        try:
            _PG_POOL.closeall()
        except Exception:
            pass
    _PG_POOL = ThreadedConnectionPool(
        minconn=_get_pg_pool_minconn(),
        maxconn=_get_pg_pool_maxconn(),
        dsn=database_url,
    )
    _PG_POOL_DSN = database_url
    logger.info(
        "Initialized PostgreSQL pool min=%s max=%s",
        _get_pg_pool_minconn(),
        _get_pg_pool_maxconn(),
    )
    return _PG_POOL


def _replace_qmark_placeholders(sql: str) -> str:
    out = []
    in_single = False
    in_double = False
    for ch in sql:
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            continue
        if ch == "?" and not in_single and not in_double:
            out.append("%s")
        else:
            out.append(ch)
    return "".join(out)


def _append_on_conflict_do_nothing(sql: str) -> str:
    body = sql.rstrip().rstrip(";")
    if "on conflict" in body.lower():
        return sql
    return f"{body} ON CONFLICT DO NOTHING;"


def _escape_pyformat_percent(sql: str) -> str:
    """
    Экранирует '%' для psycopg2 pyformat, оставляя плейсхолдеры %s нетронутыми.
    Нужен для SQL с strftime('%Y-%m-%d')/LIKE '%' при передаче params.
    """
    out = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch != "%":
            out.append(ch)
            i += 1
            continue
        nxt = sql[i + 1] if i + 1 < n else ""
        if nxt == "s":
            out.append("%s")
            i += 2
            continue
        if nxt == "%":
            out.append("%%")
            i += 2
            continue
        out.append("%%")
        i += 1
    return "".join(out)


def _optimize_date_predicates_postgres(sql: str) -> str:
    """
    Преобразует DATE(col) с параметрами в индекс-дружественные предикаты.
    Без изменения числа параметров.
    """
    col = r"([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)"
    patterns = [
        # DATE(col) >= DATE(%s)  -> col >= %s::date
        (rf"DATE\(\s*{col}\s*\)\s*>=\s*DATE\(\s*%s\s*\)", r"\1 >= %s::date"),
        # DATE(col) <= DATE(%s)  -> col < (%s::date + INTERVAL '1 day')
        (rf"DATE\(\s*{col}\s*\)\s*<=\s*DATE\(\s*%s\s*\)", r"\1 < (%s::date + INTERVAL '1 day')"),
        # DATE(col) > DATE(%s)   -> col >= (%s::date + INTERVAL '1 day')
        (rf"DATE\(\s*{col}\s*\)\s*>\s*DATE\(\s*%s\s*\)", r"\1 >= (%s::date + INTERVAL '1 day')"),
        # DATE(col) < DATE(%s)   -> col < %s::date
        (rf"DATE\(\s*{col}\s*\)\s*<\s*DATE\(\s*%s\s*\)", r"\1 < %s::date"),
    ]
    out = sql
    for pattern, replacement in patterns:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    return out


class TimedCursor(sqlite3.Cursor):
    def _log_if_slow(self, query: str, elapsed_ms: float):
        if not _get_log_slow_queries():
            return
        threshold = _get_slow_query_threshold_ms()
        if elapsed_ms < threshold:
            return
        preview = " ".join(str(query).split())
        if len(preview) > 300:
            preview = preview[:300] + "..."
        logger.warning("Slow query: %.1fms (threshold=%dms) SQL=%s", elapsed_ms, threshold, preview)

    def execute(self, query, parameters=()):
        started = time.perf_counter()
        try:
            return super().execute(query, parameters)
        finally:
            self._log_if_slow(str(query), (time.perf_counter() - started) * 1000)

    def executemany(self, query, seq_of_parameters):
        started = time.perf_counter()
        try:
            return super().executemany(query, seq_of_parameters)
        finally:
            self._log_if_slow(str(query), (time.perf_counter() - started) * 1000)


class TimedConnection(sqlite3.Connection):
    def cursor(self, *args, **kwargs):
        if "factory" not in kwargs:
            kwargs["factory"] = TimedCursor
        return super().cursor(*args, **kwargs)


class PostgresCursorAdapter:
    def __init__(self, raw_cursor, use_dict_rows: bool):
        self._cursor = raw_cursor
        self._use_dict_rows = use_dict_rows
        self._pragma_table_info_mode = False
        self._lastrowid = None

    @property
    def rowcount(self):
        return self._cursor.rowcount

    @property
    def lastrowid(self):
        if self._lastrowid is not None:
            return self._lastrowid
        return getattr(self._cursor, "lastrowid", None)

    def _extract_insert_table(self, query: str) -> Optional[str]:
        m = re.match(r'^\s*insert\s+(?:or\s+ignore\s+)?into\s+([a-zA-Z_][a-zA-Z0-9_\."]*)', query, re.IGNORECASE)
        if not m:
            return None
        raw = m.group(1).strip()
        raw = raw.replace('"', "")
        if "." not in raw:
            return f"public.{raw}"
        return raw

    def _resolve_lastrowid_after_insert(self, query: str):
        q = query.strip().lower()
        if not q.startswith("insert "):
            return
        if " returning " in q:
            return
        table_name = self._extract_insert_table(query)
        if not table_name:
            return
        aux_cursor = None
        try:
            aux_cursor = self._cursor.connection.cursor()
            table_parts = table_name.split(".", 1)
            if len(table_parts) == 2:
                table_schema = table_parts[0].replace('"', '')
                table_only = table_parts[1].replace('"', '')
            else:
                table_schema = "public"
                table_only = table_parts[0].replace('"', '')
            aux_cursor.execute(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = 'id'
                LIMIT 1
                """,
                (table_schema, table_only),
            )
            if aux_cursor.fetchone() is None:
                return
            aux_cursor.execute(
                "SELECT pg_get_serial_sequence(%s, 'id')",
                (table_name,),
            )
            seq_row = aux_cursor.fetchone()
            seq_name = seq_row[0] if seq_row else None
            if not seq_name:
                return
            aux_cursor.execute(f"SELECT last_value FROM {seq_name}")
            row = aux_cursor.fetchone()
            if row and row[0] is not None:
                self._lastrowid = int(row[0])
        except Exception:
            self._lastrowid = None
        finally:
            if aux_cursor is not None:
                try:
                    aux_cursor.close()
                except Exception:
                    pass

    def _translate_special_sql(self, query: str, parameters: Sequence[Any]) -> Tuple[str, Sequence[Any]]:
        q = query.strip()
        q_lower = q.lower()

        if q_lower.startswith("pragma "):
            pragma_table_info = re.match(r"^pragma\s+table_info\(([^)]+)\)\s*$", q_lower)
            if pragma_table_info:
                table_name = pragma_table_info.group(1).strip().strip('"').strip("'")
                self._pragma_table_info_mode = True
                sql = """
                    SELECT
                        (c.ordinal_position - 1) AS cid,
                        c.column_name AS name,
                        c.data_type AS type,
                        CASE WHEN c.is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull,
                        c.column_default AS dflt_value,
                        CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 1 ELSE 0 END AS pk
                    FROM information_schema.columns c
                    LEFT JOIN information_schema.key_column_usage kcu
                        ON c.table_schema = kcu.table_schema
                        AND c.table_name = kcu.table_name
                        AND c.column_name = kcu.column_name
                    LEFT JOIN information_schema.table_constraints tc
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                        AND tc.table_name = kcu.table_name
                    WHERE c.table_schema = 'public' AND c.table_name = %s
                    ORDER BY c.ordinal_position
                """
                return sql, (table_name,)
            if "foreign_keys" in q_lower or "journal_mode" in q_lower or "synchronous" in q_lower or "cache_size" in q_lower or "temp_store" in q_lower:
                return "SELECT 1", ()

        if "from sqlite_master" in q_lower:
            if "type='table'" in q_lower and re.search(r"and\s+name\s*=\s*\?", q_lower):
                return (
                    "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
                    tuple(parameters),
                )
            literal_table_name = re.search(r"type='table'\s+and\s+name='([^']+)'", q_lower)
            if literal_table_name:
                return (
                    "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
                    (literal_table_name.group(1),),
                )
            if "type='table'" in q_lower and "order by name" in q_lower:
                return (
                    "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name",
                    (),
                )
            if "type='index'" in q_lower and "and name=?" in q_lower:
                return (
                    "SELECT indexname AS name FROM pg_indexes WHERE schemaname='public' AND indexname=%s",
                    tuple(parameters),
                )

        if re.search(r"insert\s+or\s+ignore\s+into", q, flags=re.IGNORECASE):
            q = re.sub(r"insert\s+or\s+ignore\s+into", "INSERT INTO", q, flags=re.IGNORECASE)
            q = _append_on_conflict_do_nothing(q)

        q = _replace_qmark_placeholders(q)
        q = _optimize_date_predicates_postgres(q)
        return q, tuple(parameters)

    def execute(self, query: str, parameters: Optional[Sequence[Any]] = None):
        params = tuple(parameters) if parameters is not None else None
        self._pragma_table_info_mode = False
        self._lastrowid = None
        translated, translated_params = self._translate_special_sql(query, tuple(params or ()))
        if translated_params:
            self._cursor.execute(_escape_pyformat_percent(translated), translated_params)
        else:
            # В psycopg2 пустой tuple с '%' в SQL приводит к pyformat IndexError.
            self._cursor.execute(translated)
        self._resolve_lastrowid_after_insert(translated)
        return self

    def executemany(self, query: str, seq_of_parameters: Iterable[Sequence[Any]]):
        translated, _ = self._translate_special_sql(query, ())
        self._cursor.executemany(translated, [tuple(p) for p in seq_of_parameters])
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._pragma_table_info_mode:
            return tuple(row.values()) if isinstance(row, dict) else row
        if isinstance(row, dict):
            return CompatRow(row)
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        if self._pragma_table_info_mode:
            return [tuple(r.values()) if isinstance(r, dict) else r for r in rows]
        return [CompatRow(r) if isinstance(r, dict) else r for r in rows]

    def __iter__(self):
        for row in self._cursor:
            yield row

    def __getattr__(self, item):
        return getattr(self._cursor, item)


class PostgresConnectionAdapter:
    def __init__(self, raw_conn, row_factory=None, pool=None):
        self._conn = raw_conn
        self.row_factory = row_factory
        self._pool = pool

    def cursor(self):
        if self.row_factory and RealDictCursor is not None:
            raw = self._conn.cursor(cursor_factory=RealDictCursor)
            return PostgresCursorAdapter(raw, use_dict_rows=True)
        return PostgresCursorAdapter(self._conn.cursor(), use_dict_rows=False)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        if self._pool is not None:
            try:
                self._conn.rollback()
            except Exception:
                pass
            self._pool.putconn(self._conn)
            return None
        return self._conn.close()

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params or ())
        return cur


class CompatRow(dict):
    """Совместимая строка результата: поддерживает row['col'] и row[0]."""

    def __init__(self, source: dict):
        super().__init__(source)
        self._ordered_values = tuple(source.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._ordered_values[key]
        return super().__getitem__(key)


@contextmanager
def get_db_connection(row_factory=None, retry_on_locked=True):
    conn = None
    retries = MAX_RETRIES if retry_on_locked else 1
    driver = _get_db_driver()

    for attempt in range(retries):
        try:
            if driver == "postgres":
                if psycopg2 is None:
                    raise RuntimeError("psycopg2 не установлен. Добавьте psycopg2-binary в зависимости.")
                database_url = _get_database_url()
                if not database_url:
                    raise RuntimeError("Для PostgreSQL требуется DATABASE_URL")
                pool = _get_pg_pool(database_url)
                if pool is not None:
                    raw_conn = pool.getconn()
                    conn = PostgresConnectionAdapter(raw_conn, row_factory=row_factory, pool=pool)
                else:
                    raw_conn = psycopg2.connect(database_url, connect_timeout=10)
                    conn = PostgresConnectionAdapter(raw_conn, row_factory=row_factory)
            else:
                database_path = _get_database_path()
                db_dir = os.path.dirname(database_path)
                if db_dir and not os.path.exists(db_dir):
                    os.makedirs(db_dir, exist_ok=True)
                conn = sqlite3.connect(database_path, timeout=LOCK_TIMEOUT, factory=TimedConnection)
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA cache_size = -64000")
                conn.execute("PRAGMA temp_store = MEMORY")
                if row_factory:
                    conn.row_factory = row_factory
            break
        except Exception as e:
            msg = str(e).lower()
            is_retryable = "locked" in msg or "could not connect" in msg
            if is_retryable and retry_on_locked and attempt < retries - 1:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = None
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning("DB busy/unavailable (%s/%s), retry in %.2fs", attempt + 1, retries, wait_time)
                time.sleep(wait_time)
                continue
            logger.error("Ошибка базы данных: %s", e, exc_info=True)
            if conn:
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
            raise

    if conn is None:
        raise RuntimeError("Не удалось установить соединение с БД")

    try:
        yield conn
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def with_db_connection(row_factory=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with get_db_connection(row_factory) as conn:
                return func(conn, *args, **kwargs)
        return wrapper
    return decorator


def init_db():
    try:
        driver = _get_db_driver()
        if driver == "sqlite":
            db_path = _get_database_path()
            if not os.path.exists(db_path):
                logger.warning("База данных не найдена: %s", db_path)
                logger.info("Создание новой базы данных...")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='orders'"
                if driver == "sqlite"
                else "SELECT table_name AS name FROM information_schema.tables WHERE table_schema='public' AND table_name='orders'"
            )
            if not cursor.fetchone():
                logger.warning("Таблица 'orders' не найдена. Необходимо выполнить миграции.")
            else:
                logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error("Ошибка при инициализации БД: %s", e, exc_info=True)
        raise

