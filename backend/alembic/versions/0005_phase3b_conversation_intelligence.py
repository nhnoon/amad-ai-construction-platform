"""Phase 3B: add conversation state, context tracking, and extended audit fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ai_conversations: add conversation_state JSONB
    op.add_column(
        "ai_conversations",
        sa.Column("conversation_state", JSONB, nullable=True),
    )

    # ai_messages: add context-tracking columns
    op.add_column("ai_messages", sa.Column("original_question", sa.Text, nullable=True))
    op.add_column("ai_messages", sa.Column("resolved_query", sa.Text, nullable=True))
    op.add_column(
        "ai_messages",
        sa.Column("clarification_required", sa.Boolean, nullable=True, server_default="false"),
    )
    op.add_column("ai_messages", sa.Column("context_refs_used", sa.Integer, nullable=True))
    op.add_column("ai_messages", sa.Column("domains_used", JSONB, nullable=True))

    # copilot_audit_logs: extended Phase 3B fields
    op.add_column("copilot_audit_logs", sa.Column("original_question", sa.Text, nullable=True))
    op.add_column("copilot_audit_logs", sa.Column("resolved_query", sa.Text, nullable=True))
    op.add_column(
        "copilot_audit_logs",
        sa.Column("previous_intent", sa.String(100), nullable=True),
    )
    op.add_column(
        "copilot_audit_logs",
        sa.Column("resolved_intent", sa.String(100), nullable=True),
    )
    op.add_column("copilot_audit_logs", sa.Column("domains_used", JSONB, nullable=True))
    op.add_column(
        "copilot_audit_logs",
        sa.Column("retrieval_tools_used", JSONB, nullable=True),
    )
    op.add_column(
        "copilot_audit_logs",
        sa.Column("clarification_required", sa.Boolean, nullable=True),
    )
    op.add_column(
        "copilot_audit_logs",
        sa.Column("context_reference_count", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("copilot_audit_logs", "context_reference_count")
    op.drop_column("copilot_audit_logs", "clarification_required")
    op.drop_column("copilot_audit_logs", "retrieval_tools_used")
    op.drop_column("copilot_audit_logs", "domains_used")
    op.drop_column("copilot_audit_logs", "resolved_intent")
    op.drop_column("copilot_audit_logs", "previous_intent")
    op.drop_column("copilot_audit_logs", "resolved_query")
    op.drop_column("copilot_audit_logs", "original_question")

    op.drop_column("ai_messages", "domains_used")
    op.drop_column("ai_messages", "context_refs_used")
    op.drop_column("ai_messages", "clarification_required")
    op.drop_column("ai_messages", "resolved_query")
    op.drop_column("ai_messages", "original_question")

    op.drop_column("ai_conversations", "conversation_state")
