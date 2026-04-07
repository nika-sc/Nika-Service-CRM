"""
Утилиты миграции данных из SQLite в PostgreSQL.
"""
from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import psycopg2

logger = logging.getLogger(__name__)


@dataclass
class TableMigrationResult:
    table: str
    source_rows: int
    target_rows: int


def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _map_sqlite_type_to_pg(sqlite_type: str) -> str:
    t = (sqlite_type or "").strip().upper()
    if "INT" in t:
        return "BIGINT"
    if any(x in t for x in ("CHAR", "CLOB", "TEXT")):
        return "TEXT"
    if "BLOB" in t:
        return "BYTEA"
    if any(x in t for x in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE PRECISION"
    if any(x in t for x in ("NUMERIC", "DECIMAL")):
        return "NUMERIC"
    if "BOOL" in t:
        return "BOOLEAN"
    if "DATE" in t or "TIME" in t:
        return "TIMESTAMP"
    return "TEXT"


def _list_sqlite_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )
    return [r[0] for r in cur.fetchall()]


def _table_columns_sqlite(conn: sqlite3.Connection, table: str) -> List[Tuple]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({_quote_ident(table)})")
    return cur.fetchall()


def _create_table_in_pg(sqlite_conn: sqlite3.Connection, pg_conn, table: str):
    cols = _table_columns_sqlite(sqlite_conn, table)
    if not cols:
        return

    col_defs = []
    pk_cols = []
    for _, name, col_type, notnull, default_value, pk in cols:
        pg_type = _map_sqlite_type_to_pg(col_type)
        col_sql = f"{_quote_ident(name)} {pg_type}"
        if int(notnull or 0) == 1:
            col_sql += " NOT NULL"
        if default_value is not None:
            col_sql += f" DEFAULT {default_value}"
        col_defs.append(col_sql)
        if int(pk or 0) > 0:
            pk_cols.append((int(pk), name))

    if pk_cols:
        pk_cols.sort(key=lambda x: x[0])
        col_defs.append(
            "PRIMARY KEY (" + ", ".join(_quote_ident(c) for _, c in pk_cols) + ")"
        )

    ddl = f"CREATE TABLE IF NOT EXISTS {_quote_ident(table)} ({', '.join(col_defs)})"
    with pg_conn.cursor() as cur:
        cur.execute(ddl)
    pg_conn.commit()


def _create_indexes_in_pg(sqlite_conn: sqlite3.Connection, pg_conn, table: str):
    cur = sqlite_conn.cursor()
    cur.execute(f"PRAGMA index_list({_quote_ident(table)})")
    indexes = cur.fetchall()
    for _, idx_name, is_unique, *_rest in indexes:
        if not idx_name:
            continue
        idx_cur = sqlite_conn.cursor()
        idx_cur.execute(f"PRAGMA index_info({_quote_ident(idx_name)})")
        idx_cols = [r[2] for r in idx_cur.fetchall() if r[2]]
        if not idx_cols:
            continue
        unique_sql = "UNIQUE " if int(is_unique or 0) == 1 else ""
        pg_idx_name = f"{table}_{idx_name}_pg"
        ddl = (
            f"CREATE {unique_sql}INDEX IF NOT EXISTS {_quote_ident(pg_idx_name)} "
            f"ON {_quote_ident(table)} ({', '.join(_quote_ident(c) for c in idx_cols)})"
        )
        try:
            with pg_conn.cursor() as pg_cur:
                pg_cur.execute(ddl)
            pg_conn.commit()
        except Exception as exc:
            pg_conn.rollback()
            logger.warning("Skip index %s on table %s: %s", idx_name, table, exc)


def _copy_data(sqlite_conn: sqlite3.Connection, pg_conn, table: str, truncate: bool = False) -> TableMigrationResult:
    src_cur = sqlite_conn.cursor()
    src_cur.execute(f"SELECT * FROM {_quote_ident(table)}")
    rows = src_cur.fetchall()
    source_count = len(rows)

    cols_meta = _table_columns_sqlite(sqlite_conn, table)
    cols = [c[1] for c in cols_meta]
    if not cols:
        return TableMigrationResult(table=table, source_rows=source_count, target_rows=0)

    with pg_conn.cursor() as pg_cur:
        if truncate:
            pg_cur.execute(f"TRUNCATE TABLE {_quote_ident(table)}")

        if rows:
            placeholders = ", ".join(["%s"] * len(cols))
            insert_sql = (
                f"INSERT INTO {_quote_ident(table)} "
                f"({', '.join(_quote_ident(c) for c in cols)}) VALUES ({placeholders})"
            )
            pg_cur.executemany(insert_sql, rows)

        pg_cur.execute(f"SELECT COUNT(*) FROM {_quote_ident(table)}")
        target_count = int(pg_cur.fetchone()[0])
    pg_conn.commit()
    return TableMigrationResult(table=table, source_rows=source_count, target_rows=target_count)


def migrate_sqlite_to_postgres(
    sqlite_path: str,
    postgres_dsn: str,
    include_tables: Optional[Sequence[str]] = None,
    exclude_tables: Optional[Iterable[str]] = None,
    truncate_before_load: bool = False,
) -> Dict[str, List[TableMigrationResult]]:
    excludes = set(exclude_tables or [])
    excludes.update({"schema_migrations", "schema_migrations_pg"})

    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_conn = psycopg2.connect(postgres_dsn)
    try:
        tables = _list_sqlite_tables(sqlite_conn)
        if include_tables:
            include = set(include_tables)
            tables = [t for t in tables if t in include]
        tables = [
            t
            for t in tables
            if t not in excludes
            and not t.endswith("_fts")
            and "_fts_" not in t
        ]

        created = []
        loaded = []

        for table in tables:
            logger.info("Creating table in PostgreSQL: %s", table)
            _create_table_in_pg(sqlite_conn, pg_conn, table)
            created.append(table)

        for table in tables:
            logger.info("Copying table data: %s", table)
            result = _copy_data(sqlite_conn, pg_conn, table, truncate=truncate_before_load)
            loaded.append(result)

        for table in tables:
            logger.info("Creating indexes: %s", table)
            _create_indexes_in_pg(sqlite_conn, pg_conn, table)

        return {"tables": loaded}
    finally:
        sqlite_conn.close()
        pg_conn.close()


def validate_counts(sqlite_path: str, postgres_dsn: str, tables: Optional[Sequence[str]] = None) -> List[TableMigrationResult]:
    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_conn = psycopg2.connect(postgres_dsn)
    try:
        sqlite_tables = _list_sqlite_tables(sqlite_conn)
        excluded = {"schema_migrations", "schema_migrations_pg"}
        if tables:
            table_list = [t for t in sqlite_tables if t in set(tables)]
        else:
            table_list = [
                t
                for t in sqlite_tables
                if not t.startswith("sqlite_")
                and not t.endswith("_fts")
                and "_fts_" not in t
                and t not in excluded
            ]

        results = []
        for table in table_list:
            s_cur = sqlite_conn.cursor()
            s_cur.execute(f"SELECT COUNT(*) FROM {_quote_ident(table)}")
            src = int(s_cur.fetchone()[0])

            p_cur = pg_conn.cursor()
            try:
                p_cur.execute(f"SELECT COUNT(*) FROM {_quote_ident(table)}")
                dst = int(p_cur.fetchone()[0])
            except Exception:
                pg_conn.rollback()
                continue
            results.append(TableMigrationResult(table=table, source_rows=src, target_rows=dst))
        return results
    finally:
        sqlite_conn.close()
        pg_conn.close()
