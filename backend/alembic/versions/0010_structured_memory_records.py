"""Add AIMemoryRecord: structured, one-row-per-memory knowledge store

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_memory_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("user_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("keywords", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("citation", sa.String(50), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_ai_memory_records_org_project", "ai_memory_records",
        ["organization_id", "project_id"],
    )
    op.create_index(
        "ix_ai_memory_records_category", "ai_memory_records", ["category"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_memory_records_category", table_name="ai_memory_records")
    op.drop_index("ix_ai_memory_records_org_project", table_name="ai_memory_records")
    op.drop_table("ai_memory_records")
