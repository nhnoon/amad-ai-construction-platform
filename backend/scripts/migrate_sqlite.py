"""
Migrate SQLite dataset to PostgreSQL.

Usage:
    cd /home/runner/workspace/backend
    python -m scripts.migrate_sqlite

Steps:
  1. Load the SQL dump into an in-memory SQLite database
  2. Read every table in dependency order
  3. Insert rows into PostgreSQL
  4. Validate row counts and report
"""
import os
import sys
import sqlite3
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

SQL_DUMP = os.path.join(
    os.path.dirname(__file__),
    "../../attached_assets/sql_dataset/construction_ai_dataset_full_dump.sql",
)

TABLE_ORDER = [
    "projects",
    "suppliers",
    "subcontractors",
    "meetings",
    "project_decisions",
    "purchase_requests",
    "purchase_orders",
    "site_reports",
    "daily_activities",
    "documents",
    "generated_documents",
    "correspondence",
    "safety_events",
    "ncrs",
    "claims",
    "change_orders",
    "subcontractor_evaluations",
    "claim_evidence",
]

BOOLEAN_COLUMNS = {
    "purchase_orders": ["is_late"],
}


def load_sqlite(dump_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    with open(dump_path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)
    return conn


def get_column_names(sqlite_conn: sqlite3.Connection, table: str) -> list[str]:
    cur = sqlite_conn.execute(f"PRAGMA table_info({table})")
    return [row["name"] for row in cur.fetchall()]


def migrate_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn: psycopg2.extensions.connection,
    table: str,
) -> tuple[int, int, list[str]]:
    columns = get_column_names(sqlite_conn, table)
    bool_cols = BOOLEAN_COLUMNS.get(table, [])

    sqlite_cur = sqlite_conn.execute(f"SELECT * FROM {table}")
    rows = sqlite_cur.fetchall()
    source_count = len(rows)

    if source_count == 0:
        return 0, 0, []

    col_placeholders = ", ".join([f"%s"] * len(columns))
    col_names = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_names}) VALUES ({col_placeholders})"

    errors = []
    inserted = 0
    pg_cur = pg_conn.cursor()

    batch = []
    for row in rows:
        values = []
        for col in columns:
            val = row[col]
            if col in bool_cols:
                val = bool(val)
            values.append(val)
        batch.append(tuple(values))

    try:
        psycopg2.extras.execute_batch(pg_cur, sql, batch, page_size=500)
        pg_conn.commit()
        inserted = source_count
    except Exception as e:
        pg_conn.rollback()
        errors.append(str(e))
        inserted = 0

    return source_count, inserted, errors


def reset_sequences(pg_conn: psycopg2.extensions.connection, tables: list[str]) -> None:
    cur = pg_conn.cursor()
    for table in tables:
        try:
            cur.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1)
                )
            """)
        except Exception:
            pass
    pg_conn.commit()


def run():
    dump_path = os.path.abspath(SQL_DUMP)
    if not os.path.exists(dump_path):
        print(f"ERROR: SQL dump not found at {dump_path}")
        sys.exit(1)

    print(f"Loading SQLite dump from: {dump_path}")
    sqlite_conn = load_sqlite(dump_path)
    print("SQLite loaded into memory.")

    print(f"Connecting to PostgreSQL: {settings.DATABASE_URL.split('@')[-1]}")
    pg_conn = psycopg2.connect(settings.DATABASE_URL)

    print("\n{'='*60}")
    print(f"{'Table':<35} {'Source':>8} {'Inserted':>10} {'Status':>10}")
    print("-" * 65)

    total_source = 0
    total_inserted = 0
    all_errors = {}

    for table in TABLE_ORDER:
        src, ins, errs = migrate_table(sqlite_conn, pg_conn, table)
        total_source += src
        total_inserted += ins
        status = "OK" if not errs else "ERROR"
        print(f"{table:<35} {src:>8} {ins:>10} {status:>10}")
        if errs:
            all_errors[table] = errs

    reset_sequences(pg_conn, TABLE_ORDER)

    print("-" * 65)
    print(f"{'TOTAL':<35} {total_source:>8} {total_inserted:>10}")
    print()

    if all_errors:
        print("MIGRATION ERRORS:")
        for table, errs in all_errors.items():
            print(f"  {table}: {errs[0]}")
        sys.exit(1)
    else:
        print("Migration completed successfully.")

    pg_conn.close()
    sqlite_conn.close()


if __name__ == "__main__":
    run()
