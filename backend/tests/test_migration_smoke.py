"""Phase 1 production-hardening — automated migration smoke test (Part D
item 1: "clean DB migrates base -> head").

Creates a genuinely empty, disposable Postgres database (same server as
the app's real DATABASE_URL, different database name) and runs
`alembic upgrade head` against it via the Alembic Python API — the same
way a fresh production deployment would. This is what originally caught
both Phase-1 blockers (the duplicate user_accounts table, and the
pgvector extension being unavailable) — reading the migration files was
not enough; only actually running them against an empty database exposed
the failures. Skips (does not fail) if the DB role lacks CREATEDB/DROPDB
privilege, since that is an environment limitation, not a code defect.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import psycopg2
import pytest
from psycopg2 import errors as pg_errors

from app.config import settings

_TEST_DB_NAME = "amad_migration_smoke_test"


def _admin_connect():
    u = urlparse(settings.DATABASE_URL)
    conn = psycopg2.connect(
        host=u.hostname, port=u.port, user=u.username, password=u.password,
        dbname="postgres",
    )
    conn.autocommit = True
    return conn


def _smoke_test_url() -> str:
    return re.sub(r"/[^/]+$", f"/{_TEST_DB_NAME}", settings.DATABASE_URL)


@pytest.fixture
def fresh_empty_database(monkeypatch):
    try:
        conn = _admin_connect()
    except Exception as exc:
        pytest.skip(f"Cannot connect to Postgres as admin to manage a throwaway DB: {exc}")
        return

    cur = conn.cursor()
    try:
        cur.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
        cur.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    except pg_errors.InsufficientPrivilege as exc:
        cur.close()
        conn.close()
        pytest.skip(f"DB role lacks CREATEDB privilege: {exc}")
        return

    url = _smoke_test_url()
    # alembic/env.py reads `settings.DATABASE_URL` directly (re-asserting
    # it into the Alembic Config at import time), not whatever URL is
    # passed into Config.set_main_option — so the settings singleton
    # itself must be patched, not just the Config object or os.environ.
    monkeypatch.setattr(settings, "DATABASE_URL", url)

    yield url

    cur.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
    cur.close()
    conn.close()


class TestFreshDatabaseMigratesToHead:
    def test_alembic_upgrade_head_succeeds_on_empty_database(self, fresh_empty_database):
        from alembic import command
        from alembic.config import Config

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", fresh_empty_database)
        command.upgrade(cfg, "head")

        conn = psycopg2.connect(fresh_empty_database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT version_num FROM alembic_version")
            (head,) = cur.fetchone()
            assert head == "0021"

            # The exact bug this migration chain fixes: user_accounts must
            # exist exactly once (0001 used to create it, then 0002 created
            # it again unconditionally -> "table already exists" on a fresh DB).
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'user_accounts'"
            )
            assert cur.fetchone()[0] == 1

            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'user_accounts' ORDER BY ordinal_position"
            )
            cols = {row[0] for row in cur.fetchall()}
            assert {
                "id", "email", "hashed_password", "full_name", "role",
                "is_active", "created_at", "last_login", "organization_id",
            }.issubset(cols)

            # projects.organization_id must exist and be NOT NULL-capable
            # (Part B root tenant-ownership column).
            cur.execute(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'projects' AND column_name = 'organization_id'"
            )
            assert cur.fetchone()[0] == "NO"
        finally:
            conn.close()

    def test_alembic_upgrade_head_is_idempotent(self, fresh_empty_database):
        """Running upgrade head twice on an already-migrated DB must be a
        no-op, not an error (guards against non-idempotent migrations like
        the original 0001/0002 duplicate user_accounts bug)."""
        from alembic import command
        from alembic.config import Config

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", fresh_empty_database)
        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")  # must not raise
