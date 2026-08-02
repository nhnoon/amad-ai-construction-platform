"""Add Notifications Engine (Sprint 4): persistent, user-scoped in-app
notifications + supporting indexes.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-02

Purely additive — one new table, zero changes to any table from a prior
sprint (no columns added/dropped/renamed on projects/risks/issues/action
items/safety events/ncrs/purchase requests/user_accounts/organizations).
No backfill needed: notifications did not exist before this table, so
there is no legacy data to migrate.

Indexes mirror the actual query shapes Sprint 4 needs (see
app/api/v1/notifications.py): recipient_user_id / is_read / created_at /
project_id individually, a composite (recipient_user_id, is_read,
created_at) for the "my unread, newest first" hot path, and a unique
index on deduplication_key so app/ai/notification_service.py can rely on
a single atomic INSERT ... ON CONFLICT DO NOTHING for dedup instead of a
check-then-insert race.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("action_url", sa.String(500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deduplication_key", sa.String(255), nullable=True),
    )
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notifications_project_id", "notifications", ["project_id"])
    op.create_index(
        "ix_notifications_recipient_unread_created", "notifications",
        ["recipient_user_id", "is_read", "created_at"],
    )
    op.create_index("ix_notifications_dedup_key", "notifications", ["deduplication_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_notifications_dedup_key", table_name="notifications")
    op.drop_index("ix_notifications_recipient_unread_created", table_name="notifications")
    op.drop_index("ix_notifications_project_id", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_recipient_user_id", table_name="notifications")
    op.drop_table("notifications")
