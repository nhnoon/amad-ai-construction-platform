"""Add B2B SaaS foundation: organizations, project_memberships, user org_id

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # 2. Add organization_id to user_accounts (nullable — preserves all existing rows)
    op.add_column(
        "user_accounts",
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_user_accounts_org_id", "user_accounts", ["organization_id"])

    # 3. project_memberships table
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("user_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_on_project", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_project_memberships_user_id", "project_memberships", ["user_id"])
    op.create_index("ix_project_memberships_project_id", "project_memberships", ["project_id"])
    op.create_unique_constraint(
        "uq_project_membership", "project_memberships", ["user_id", "project_id"]
    )


def downgrade() -> None:
    op.drop_table("project_memberships")
    op.drop_index("ix_user_accounts_org_id", table_name="user_accounts")
    op.drop_column("user_accounts", "organization_id")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
