"""RC1 Phase 1 Sprint 4 — Enterprise Audit Logging: add audit_logs, an
append-only record of every security-sensitive/mutating action covered
this sprint (see app/models/audit.py::AuditLog and
app/core/audit_log.py::record_audit_event, the table's only writer).

Purely additive — a brand-new table, no existing column touched.

Immutability is enforced at the database level, not just by the
application never writing an UPDATE/DELETE: a trigger rejects both
outright on this table. This is deliberately stronger than "the app
doesn't expose an endpoint for it" — it holds even against a future bug
or an ad-hoc admin script that bypasses the ORM. organization_id /
actor_user_id / project_id all use ondelete="SET NULL" so an audit row
is never lost just because the entity it referenced was later deleted —
losing the dangling reference is fine; losing the row would defeat the
whole feature.

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "event_id", postgresql.UUID(as_uuid=True), nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "organization_id", sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "actor_user_id", sa.Integer(),
            sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "project_id", sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_audit_logs_event_id", "audit_logs", ["event_id"], unique=True)
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_project_id", "audit_logs", ["project_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # Postgres's built-in pgcrypto/pgcrypto-free gen_random_uuid() is
    # available by default from PG13+ (this project targets a recent
    # Postgres — see backend/.env.example) without needing to CREATE
    # EXTENSION; used only as the server-side default so a row is never
    # left without an event_id even if application code somehow omitted
    # it, mirroring the model's Python-side default=uuid.uuid4 as
    # belt-and-suspenders, not a replacement for it.

    # ── Immutability trigger ────────────────────────────────────────
    # One narrow, deliberate exception: organization_id/actor_user_id/
    # project_id all use ondelete="SET NULL" (see model docstring — an
    # audit ROW must never be lost just because the org/user/project it
    # referenced was later deleted). Postgres implements ON DELETE SET
    # NULL as an actual UPDATE nulling out the referencing column(s),
    # which a blanket "reject every UPDATE" trigger would itself reject —
    # breaking the ability to ever delete a referenced organization/user/
    # project at all. This function allows exactly that one case (an FK
    # column transitioning to NULL, and nothing else) through, while
    # still rejecting any change to the actual audit content
    # (action/result/before_state/after_state/reason/timestamps/etc.) or
    # any attempt to reassign an FK column to a *different* non-null
    # value — i.e. what happened, and who/what it was attributed to,
    # remains genuinely tamper-proof; only the referential-integrity
    # side effect of a referenced row's deletion is accommodated.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_logs_prevent_mutation() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'audit_logs rows are append-only and immutable; DELETE is not permitted on this table';
            END IF;

            IF NEW.event_id IS DISTINCT FROM OLD.event_id
               OR NEW.created_at IS DISTINCT FROM OLD.created_at
               OR NEW.entity_type IS DISTINCT FROM OLD.entity_type
               OR NEW.entity_id IS DISTINCT FROM OLD.entity_id
               OR NEW.action IS DISTINCT FROM OLD.action
               OR NEW.result IS DISTINCT FROM OLD.result
               OR NEW.ip_address IS DISTINCT FROM OLD.ip_address
               OR NEW.user_agent IS DISTINCT FROM OLD.user_agent
               OR NEW.request_id IS DISTINCT FROM OLD.request_id
               OR NEW.before_state IS DISTINCT FROM OLD.before_state
               OR NEW.after_state IS DISTINCT FROM OLD.after_state
               OR NEW.reason IS DISTINCT FROM OLD.reason
               OR (NEW.organization_id IS NOT NULL AND NEW.organization_id IS DISTINCT FROM OLD.organization_id)
               OR (NEW.actor_user_id IS NOT NULL AND NEW.actor_user_id IS DISTINCT FROM OLD.actor_user_id)
               OR (NEW.project_id IS NOT NULL AND NEW.project_id IS DISTINCT FROM OLD.project_id)
            THEN
                RAISE EXCEPTION 'audit_logs rows are append-only and immutable; UPDATE is not permitted on this table (except FK nullification when a referenced organization/user/project is deleted)';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_no_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_prevent_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_no_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_prevent_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_delete ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update ON audit_logs;")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_prevent_mutation();")

    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_project_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_organization_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_id", table_name="audit_logs")
    op.drop_table("audit_logs")
