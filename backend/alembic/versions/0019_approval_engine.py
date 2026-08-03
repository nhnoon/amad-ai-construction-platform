"""Add Approval Engine (Sprint 5): evolve the previously-unused
approval_requests table into a real per-entity approve/reject workflow,
plus append-only approval_history.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-02

approval_requests existed before this migration (see the original
ApprovalRequest model, formerly in app/models/ai.py) but had zero real
call sites anywhere in the codebase and was shaped for a different,
never-built use case: AI-agent action approval (action_type,
action_description, payload, a free-text requested_by defaulting to
"ai_agent"). Since the table has no real rows to preserve, this
migration is still written additive/null-safe throughout, matching
0017/0018's own discipline, rather than assuming emptiness:

  - action_type / action_description are relaxed from NOT NULL to
    nullable (never dropped or renamed) — Sprint 5's own rows never
    populate them; they remain available if that original AI-agent-
    approval use case is ever built.
  - Every Sprint 5 column is added nullable at the DB level (validated
    at the API layer instead — this codebase's consistent convention for
    every *.status/workflow vocabulary column; see
    app/ai/approval_engine.py).
  - organization_id / requested_by_user_id / assigned_reviewer_id /
    reviewed_by_user_id all use ondelete="SET NULL" (preserve the
    approval record even if the referenced account/org is later
    removed) — organization_id specifically mirrors
    Document.organization_id's existing SET NULL precedent.
  - target_version (DocumentVersion.version_number an approval applies
    to) is Document-specific and NULL for every other entity_type.

New approval_history table mirrors assignment_history (migration 0017)
exactly: append-only, one row per lifecycle transition, CASCADE on its
parent approval_request_id.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("approval_requests", "action_type", existing_type=sa.String(100), nullable=True)
    op.alter_column("approval_requests", "action_description", existing_type=sa.Text(), nullable=True)

    op.add_column("approval_requests", sa.Column("organization_id", sa.Integer(), nullable=True))
    op.add_column("approval_requests", sa.Column("entity_type", sa.String(50), nullable=True))
    op.add_column("approval_requests", sa.Column("entity_id", sa.Integer(), nullable=True))
    op.add_column("approval_requests", sa.Column("requested_by_user_id", sa.Integer(), nullable=True))
    op.add_column("approval_requests", sa.Column("assigned_reviewer_id", sa.Integer(), nullable=True))
    op.add_column("approval_requests", sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True))
    op.add_column("approval_requests", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("approval_requests", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.add_column("approval_requests", sa.Column("target_version", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_approval_requests_organization_id_organizations", "approval_requests", "organizations",
        ["organization_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_approval_requests_requested_by_user_id_user_accounts", "approval_requests", "user_accounts",
        ["requested_by_user_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_approval_requests_assigned_reviewer_id_user_accounts", "approval_requests", "user_accounts",
        ["assigned_reviewer_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_approval_requests_reviewed_by_user_id_user_accounts", "approval_requests", "user_accounts",
        ["reviewed_by_user_id"], ["id"], ondelete="SET NULL",
    )

    op.create_index("ix_approval_requests_project_id", "approval_requests", ["project_id"])
    op.create_index("ix_approval_requests_organization_id", "approval_requests", ["organization_id"])
    op.create_index("ix_approval_requests_entity", "approval_requests", ["entity_type", "entity_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_assigned_reviewer_id", "approval_requests", ["assigned_reviewer_id"])
    op.create_index("ix_approval_requests_requested_by_user_id", "approval_requests", ["requested_by_user_id"])
    op.create_index("ix_approval_requests_due_at", "approval_requests", ["due_at"])

    op.create_table(
        "approval_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("approval_request_id", sa.Integer(), sa.ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(50), nullable=True),
        sa.Column("new_status", sa.String(50), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_approval_history_approval_request_id", "approval_history", ["approval_request_id"])


def downgrade() -> None:
    op.drop_index("ix_approval_history_approval_request_id", table_name="approval_history")
    op.drop_table("approval_history")

    op.drop_index("ix_approval_requests_due_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_requested_by_user_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_assigned_reviewer_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_entity", table_name="approval_requests")
    op.drop_index("ix_approval_requests_organization_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_project_id", table_name="approval_requests")

    op.drop_constraint("fk_approval_requests_reviewed_by_user_id_user_accounts", "approval_requests", type_="foreignkey")
    op.drop_constraint("fk_approval_requests_assigned_reviewer_id_user_accounts", "approval_requests", type_="foreignkey")
    op.drop_constraint("fk_approval_requests_requested_by_user_id_user_accounts", "approval_requests", type_="foreignkey")
    op.drop_constraint("fk_approval_requests_organization_id_organizations", "approval_requests", type_="foreignkey")

    op.drop_column("approval_requests", "target_version")
    op.drop_column("approval_requests", "updated_at")
    op.drop_column("approval_requests", "due_at")
    op.drop_column("approval_requests", "reviewed_by_user_id")
    op.drop_column("approval_requests", "assigned_reviewer_id")
    op.drop_column("approval_requests", "requested_by_user_id")
    op.drop_column("approval_requests", "entity_id")
    op.drop_column("approval_requests", "entity_type")
    op.drop_column("approval_requests", "organization_id")

    op.alter_column("approval_requests", "action_description", existing_type=sa.Text(), nullable=False)
    op.alter_column("approval_requests", "action_type", existing_type=sa.String(100), nullable=False)
