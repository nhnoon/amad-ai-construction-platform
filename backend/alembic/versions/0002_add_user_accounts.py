"""Add user_accounts table for authentication

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Defensive idempotency guard (Phase 1 production-hardening migration
    # repair): this is the sole, original migration that creates
    # user_accounts — 0001_initial_schema.py used to also contain a
    # duplicate, unconditional create of this same table, which has since
    # been removed there. This existence check is a second layer of
    # protection against that specific class of bug reappearing (e.g. via a
    # future rebase/cherry-pick, or a database that was seeded by some other
    # means before this migration chain ran): if user_accounts already
    # exists for any reason, skip creating it again but still make sure the
    # named unique index exists, since that's the one piece of this
    # migration nothing else in the chain provides.
    bind = op.get_bind()
    inspector = inspect(bind)
    table_exists = "user_accounts" in inspector.get_table_names()

    if not table_exists:
        op.create_table(
            "user_accounts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("full_name", sa.String(255), nullable=True),
            sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        )
        inspector = inspect(bind)  # refresh — table now exists

    existing_index_names = {ix["name"] for ix in inspector.get_indexes("user_accounts")}
    if "ix_user_accounts_email" not in existing_index_names:
        op.create_index("ix_user_accounts_email", "user_accounts", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_accounts_email", table_name="user_accounts")
    op.drop_table("user_accounts")
