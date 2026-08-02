"""Add Ownership Engine: real user assignment for risks, issues, action
items, safety events, NCRs, purchase requests + assignment history

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-02

Additive and null-safe throughout:
  - owner_id / assigned_by / assigned_at are added to all six tables,
    all nullable. The three tables that already had a free-text `owner`
    column (project_risks, project_issues, meeting_action_items) keep it
    completely untouched — no data is ever lost, no column is dropped or
    renamed.
  - A deterministic, ambiguity-safe backfill then attempts to populate
    owner_id on those three tables from the existing `owner` text: for
    each non-empty owner string, look up user_accounts in the SAME
    organization as the entity's project whose full_name or email
    case-insensitively matches. owner_id is only ever set when EXACTLY
    ONE such user exists — an ambiguous (0 or 2+) match leaves owner_id
    NULL and the `owner` text exactly as it was. See
    app/ai/ownership_engine.py for the live assign/unassign path that
    supersedes this one-time backfill going forward.
  - safety_events, ncrs, purchase_requests never had a free-text owner
    concept at all — owner_id is simply new, NULL for every existing row
    (nothing to backfill from).
  - Indexes added on owner_id (all six) and status (the four tables that
    didn't already have one — purchase_requests already did) and
    meeting_action_items.due_date, so the "assigned to me / assigned to
    user / unassigned / overdue / open" queries this sprint adds never
    need a sequential scan.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEGACY_OWNER_TABLES = ("project_risks", "project_issues", "meeting_action_items")
_NO_LEGACY_OWNER_TABLES = ("safety_events", "ncrs", "purchase_requests")


def _add_ownership_columns(table: str) -> None:
    op.add_column(table, sa.Column("owner_id", sa.Integer(), nullable=True))
    op.add_column(table, sa.Column("assigned_by", sa.Integer(), nullable=True))
    op.add_column(table, sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        f"fk_{table}_owner_id_user_accounts", table, "user_accounts",
        ["owner_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        f"fk_{table}_assigned_by_user_accounts", table, "user_accounts",
        ["assigned_by"], ["id"], ondelete="SET NULL",
    )
    op.create_index(f"ix_{table}_owner_id", table, ["owner_id"])


def backfill_owner_id_from_owner_text(conn, table: str) -> None:
    """Python-driven, not a single SQL UPDATE...FROM, specifically so
    ambiguous matches (2+ users with the same name in one organization)
    are detected and skipped rather than silently resolved to whichever
    row the database happens to join first. Takes a connection directly
    (rather than calling op.get_bind() itself) so it's callable from a
    plain test with a real engine connection, not just from inside a live
    alembic migration context — see tests/test_ownership_engine.py."""
    rows = conn.execute(sa.text(
        f"""
        SELECT r.id, r.owner, p.organization_id
        FROM {table} r
        JOIN projects p ON p.id = r.project_id
        WHERE r.owner IS NOT NULL AND TRIM(r.owner) <> ''
        """
    )).fetchall()

    for row_id, owner_text, organization_id in rows:
        candidates = conn.execute(
            sa.text(
                """
                SELECT id FROM user_accounts
                WHERE organization_id = :org_id
                  AND (
                    LOWER(TRIM(COALESCE(full_name, ''))) = LOWER(TRIM(:owner_text))
                    OR LOWER(email) = LOWER(TRIM(:owner_text))
                  )
                """
            ),
            {"org_id": organization_id, "owner_text": owner_text},
        ).fetchall()
        if len(candidates) == 1:
            conn.execute(
                sa.text(f"UPDATE {table} SET owner_id = :uid WHERE id = :rid"),
                {"uid": candidates[0][0], "rid": row_id},
            )


def upgrade() -> None:
    for table in _LEGACY_OWNER_TABLES + _NO_LEGACY_OWNER_TABLES:
        _add_ownership_columns(table)

    conn = op.get_bind()
    for table in _LEGACY_OWNER_TABLES:
        backfill_owner_id_from_owner_text(conn, table)

    # Query-efficiency indexes (Sprint 3 §"Queries") — status didn't
    # already have one on these four; purchase_requests.status already
    # does (see migration 0001). meeting_action_items.due_date backs the
    # "overdue" query.
    op.create_index("ix_project_risks_status", "project_risks", ["status"])
    op.create_index("ix_project_issues_status", "project_issues", ["status"])
    op.create_index("ix_meeting_action_items_status", "meeting_action_items", ["status"])
    op.create_index("ix_meeting_action_items_due_date", "meeting_action_items", ["due_date"])
    op.create_index("ix_safety_events_status", "safety_events", ["status"])
    op.create_index("ix_ncrs_status", "ncrs", ["status"])

    op.create_table(
        "assignment_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_owner_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("new_owner_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_assignment_history_entity", "assignment_history", ["entity_type", "entity_id"])
    op.create_index("ix_assignment_history_project_id", "assignment_history", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_assignment_history_project_id", table_name="assignment_history")
    op.drop_index("ix_assignment_history_entity", table_name="assignment_history")
    op.drop_table("assignment_history")

    op.drop_index("ix_ncrs_status", table_name="ncrs")
    op.drop_index("ix_safety_events_status", table_name="safety_events")
    op.drop_index("ix_meeting_action_items_due_date", table_name="meeting_action_items")
    op.drop_index("ix_meeting_action_items_status", table_name="meeting_action_items")
    op.drop_index("ix_project_issues_status", table_name="project_issues")
    op.drop_index("ix_project_risks_status", table_name="project_risks")

    for table in _NO_LEGACY_OWNER_TABLES + _LEGACY_OWNER_TABLES:
        op.drop_index(f"ix_{table}_owner_id", table_name=table)
        op.drop_constraint(f"fk_{table}_assigned_by_user_accounts", table, type_="foreignkey")
        op.drop_constraint(f"fk_{table}_owner_id_user_accounts", table, type_="foreignkey")
        op.drop_column(table, "assigned_at")
        op.drop_column(table, "assigned_by")
        op.drop_column(table, "owner_id")
