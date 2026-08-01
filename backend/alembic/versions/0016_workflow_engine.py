"""Add Core Workflow Engine: status transitions for risks, issues, action
items, safety events, NCRs, purchase requests

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-01

Every column added here is nullable or defaulted so existing rows (and
existing GET/POST behavior) are unaffected:
  - project_risks / project_issues / meeting_action_items: updated_at
    (system audit timestamp, DateTime — matches the convention already
    used by document_ocr_results/documents, not the legacy String(50)
    business-date convention used by fields like due_date/resolved_at)
    + updated_by (nullable FK -> user_accounts, SET NULL — same pattern
    as documents.uploaded_by / document_ocr_results.requested_by).
  - meeting_action_items also gets completed_at (String(50) — matches
    its sibling field ProjectIssue.resolved_at's existing type, a
    business-meaningful close-out date, not a system timestamp).
  - safety_events gets a NEW status column (String(50), NOT NULL,
    server_default 'Open') — this table previously had no status concept
    at all; every existing row is backfilled to 'Open' by the server
    default, matching NCR's own "Open" initial state for a sibling
    safety/quality entity in the same table group.
  - ncrs gets a NEW corrective_action column (Text, nullable) — required
    to actually close an NCR under the new workflow rules; NULL for every
    existing row until explicitly set via the new PATCH endpoint.
  - purchase_requests gets updated_at + updated_by only (its own
    created_at already exists as a String(50) business-date column and
    is left untouched).

See app/ai/workflow_engine.py for what populates these.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_audit_columns(table: str) -> None:
    op.add_column(
        table,
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(table, sa.Column("updated_by", sa.Integer(), nullable=True))
    op.create_foreign_key(
        f"fk_{table}_updated_by_user_accounts", table, "user_accounts",
        ["updated_by"], ["id"], ondelete="SET NULL",
    )


def upgrade() -> None:
    _add_audit_columns("project_risks")
    _add_audit_columns("project_issues")

    _add_audit_columns("meeting_action_items")
    op.add_column("meeting_action_items", sa.Column("completed_at", sa.String(50), nullable=True))

    op.add_column(
        "safety_events",
        sa.Column("status", sa.String(50), nullable=False, server_default="Open"),
    )
    _add_audit_columns("safety_events")

    op.add_column("ncrs", sa.Column("corrective_action", sa.Text(), nullable=True))
    _add_audit_columns("ncrs")

    _add_audit_columns("purchase_requests")


def _drop_audit_columns(table: str) -> None:
    op.drop_constraint(f"fk_{table}_updated_by_user_accounts", table, type_="foreignkey")
    op.drop_column(table, "updated_by")
    op.drop_column(table, "updated_at")


def downgrade() -> None:
    _drop_audit_columns("purchase_requests")

    _drop_audit_columns("ncrs")
    op.drop_column("ncrs", "corrective_action")

    _drop_audit_columns("safety_events")
    op.drop_column("safety_events", "status")

    op.drop_column("meeting_action_items", "completed_at")
    _drop_audit_columns("meeting_action_items")

    _drop_audit_columns("project_issues")
    _drop_audit_columns("project_risks")
