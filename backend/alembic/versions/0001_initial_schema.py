"""Initial schema — all 18 dataset tables + 9 new extension tables

Revision ID: 0001
Revises:
Create Date: 2026-07-05
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── DATASET TABLES ────────────────────────────────────────────────────────

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_code", sa.String(50), nullable=False, unique=True),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column("project_type", sa.String(100), nullable=False),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("start_date", sa.String(50), nullable=False),
        sa.Column("planned_finish", sa.String(50), nullable=False),
        sa.Column("actual_finish", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("budget", sa.Float(), nullable=False),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
    )

    op.create_table(
        "subcontractors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trade", sa.String(100), nullable=False),
        sa.Column("contact_person", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("classification", sa.String(50), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("created_at", sa.String(50), nullable=False),
    )

    op.create_table(
        "meetings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("meeting_date", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("meeting_type", sa.String(100), nullable=False),
    )

    op.create_table(
        "project_decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("decision_date", sa.String(50), nullable=False),
        sa.Column("decision_text", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
    )

    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("request_no", sa.String(50), nullable=False),
        sa.Column("material_category", sa.String(100), nullable=True),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("required_delivery_date", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("rework_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(50), nullable=False),
    )

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pr_id", sa.Integer(), sa.ForeignKey("purchase_requests.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("po_number", sa.String(50), nullable=False),
        sa.Column("issue_date", sa.String(50), nullable=False),
        sa.Column("promised_delivery", sa.String(50), nullable=False),
        sa.Column("actual_delivery", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("is_late", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("delay_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delay_root_cause", sa.Text(), nullable=True),
    )

    op.create_table(
        "site_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("report_date", sa.String(50), nullable=False),
        sa.Column("weather", sa.String(100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
    )

    op.create_table(
        "daily_activities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("subcontractor_id", sa.Integer(), sa.ForeignKey("subcontractors.id"), nullable=False),
        sa.Column("site_report_id", sa.Integer(), sa.ForeignKey("site_reports.id"), nullable=False),
        sa.Column("activity_date", sa.String(50), nullable=False),
        sa.Column("activity_description", sa.Text(), nullable=False),
        sa.Column("manpower_count", sa.Integer(), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("doc_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("doc_date", sa.String(50), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=False),
    )

    op.create_table(
        "generated_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("related_record_id", sa.Integer(), nullable=False),
        sa.Column("document_date", sa.String(50), nullable=False),
        sa.Column("sender", sa.String(255), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
    )

    op.create_table(
        "correspondence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("related_record_type", sa.String(100), nullable=False),
        sa.Column("related_record_id", sa.Integer(), nullable=False),
        sa.Column("sent_date", sa.String(50), nullable=False),
        sa.Column("sender", sa.String(255), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
    )

    op.create_table(
        "safety_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("subcontractor_id", sa.Integer(), sa.ForeignKey("subcontractors.id"), nullable=False),
        sa.Column("event_date", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("corrective_action", sa.Text(), nullable=False),
    )

    op.create_table(
        "ncrs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True),
        sa.Column("subcontractor_id", sa.Integer(), sa.ForeignKey("subcontractors.id"), nullable=True),
        sa.Column("ncr_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("issue_date", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
    )

    op.create_table(
        "claims",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("claim_number", sa.String(50), nullable=False),
        sa.Column("claim_type", sa.String(100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
    )

    op.create_table(
        "change_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("co_number", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
    )

    op.create_table(
        "subcontractor_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subcontractor_id", sa.Integer(), sa.ForeignKey("subcontractors.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("evaluation_date", sa.String(50), nullable=False),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("safety_score", sa.Integer(), nullable=False),
        sa.Column("schedule_score", sa.Integer(), nullable=False),
        sa.Column("manpower_score", sa.Integer(), nullable=False),
        sa.Column("overall_rating", sa.Float(), nullable=False),
        sa.Column("comments", sa.Text(), nullable=False),
        sa.Column("linked_safety_event_id", sa.Integer(), sa.ForeignKey("safety_events.id"), nullable=True),
        sa.Column("linked_ncr_id", sa.Integer(), sa.ForeignKey("ncrs.id"), nullable=True),
        sa.Column("linked_daily_activity_id", sa.Integer(), sa.ForeignKey("daily_activities.id"), nullable=True),
    )

    op.create_table(
        "claim_evidence",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("change_order_id", sa.Integer(), sa.ForeignKey("change_orders.id"), nullable=False),
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("project_decisions.id"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("correspondence_id", sa.Integer(), sa.ForeignKey("correspondence.id"), nullable=False),
        sa.Column("evidence_note", sa.Text(), nullable=False),
    )

    # ── EXTENSION TABLES ──────────────────────────────────────────────────────

    op.create_table(
        "project_phases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("start_date", sa.String(50), nullable=True),
        sa.Column("end_date", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="planned"),
    )

    op.create_table(
        "project_milestones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("phase_id", sa.Integer(), sa.ForeignKey("project_phases.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("planned_date", sa.String(50), nullable=False),
        sa.Column("actual_date", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
    )

    op.create_table(
        "project_risks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("probability", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("impact", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(50), nullable=True),
    )

    op.create_table(
        "project_issues",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(50), nullable=True),
        sa.Column("resolved_at", sa.String(50), nullable=True),
    )

    op.create_table(
        "meeting_attendees",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("organization", sa.String(255), nullable=True),
    )

    op.create_table(
        "meeting_action_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("due_date", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
    )

    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "ai_memories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(100), nullable=False, server_default="ai_agent"),
    )

    op.execute(
        "ALTER TABLE ai_memories ALTER COLUMN embedding TYPE vector(1536) "
        "USING NULL"
    )

    op.create_table(
        "ai_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workflow_name", sa.String(100), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=False),
        sa.Column("memory_ids_used", JSONB(), nullable=True),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approval_status", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("requested_by", sa.String(100), nullable=False, server_default="ai_agent"),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── INDEXES ───────────────────────────────────────────────────────────────
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_purchase_requests_project_id", "purchase_requests", ["project_id"])
    op.create_index("ix_purchase_requests_status", "purchase_requests", ["status"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_is_late", "purchase_orders", ["is_late"])
    op.create_index("ix_site_reports_project_id", "site_reports", ["project_id"])
    op.create_index("ix_safety_events_project_id", "safety_events", ["project_id"])
    op.create_index("ix_ncrs_project_id", "ncrs", ["project_id"])
    op.create_index("ix_ai_memories_project_id", "ai_memories", ["project_id"])
    op.create_index("ix_ai_memories_category", "ai_memories", ["category"])


def downgrade() -> None:
    tables = [
        "approval_requests", "ai_audit_logs", "ai_memories", "user_accounts",
        "meeting_action_items", "meeting_attendees", "project_issues", "project_risks",
        "project_milestones", "project_phases", "claim_evidence", "subcontractor_evaluations",
        "change_orders", "claims", "ncrs", "safety_events", "correspondence",
        "generated_documents", "documents", "daily_activities", "site_reports",
        "purchase_orders", "purchase_requests", "project_decisions", "meetings",
        "subcontractors", "suppliers", "projects",
    ]
    for t in tables:
        op.drop_table(t)
    op.execute("DROP EXTENSION IF EXISTS vector")
