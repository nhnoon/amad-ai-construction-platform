"""Phase 2 — Security & Authentication Hardening: add first-login password
change enforcement and login brute-force protection columns to
user_accounts.

All three columns are purely additive with safe, inert defaults, so every
existing row is backfilled without being forced into a new behavior:

- must_change_password: defaults to false for existing rows (Phase 2's
  "do not break existing users" requirement) — application code explicitly
  sets this true only for newly created accounts (POST /auth/register,
  POST /admin/users) and clears it once the user completes a real password
  change (POST /auth/change-password).
- failed_login_attempts / locked_until: fresh counters, meaningless for
  existing rows until a future failed/successful login touches them.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-21
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_accounts",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "user_accounts",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_accounts",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_accounts", "locked_until")
    op.drop_column("user_accounts", "failed_login_attempts")
    op.drop_column("user_accounts", "must_change_password")
