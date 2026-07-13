"""Support General Library (organization-scoped) documents

Makes Document.project_id nullable and adds Document.organization_id, so a
document can be either project-scoped (project_id set) or an
organization-scoped General Library document (project_id NULL,
organization_id required). document_ocr_results.project_id and
contract_extractions.project_id become nullable to match — those tables
already carry organization_id (added in earlier migrations).

Preserves all existing rows: no data is deleted or recreated. Existing
Document rows keep their current project_id (all were project-scoped
before this migration) and get organization_id = NULL, which is valid
under the new CHECK constraint since project_id remains NOT NULL for them.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-13
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # documents: project_id -> nullable, add organization_id, add CHECK
    op.alter_column("documents", "project_id", existing_type=sa.Integer(), nullable=True)
    op.add_column(
        "documents",
        sa.Column(
            "organization_id", sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_documents_organization_id", "documents", ["organization_id"])
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_check_constraint(
        "ck_documents_project_or_org",
        "documents",
        "project_id IS NOT NULL OR organization_id IS NOT NULL",
    )

    # document_ocr_results / contract_extractions: project_id -> nullable
    # (organization_id already exists on both, added in 0007/0008).
    op.alter_column(
        "document_ocr_results", "project_id", existing_type=sa.Integer(), nullable=True
    )
    op.alter_column(
        "contract_extractions", "project_id", existing_type=sa.Integer(), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "contract_extractions", "project_id", existing_type=sa.Integer(), nullable=False
    )
    op.alter_column(
        "document_ocr_results", "project_id", existing_type=sa.Integer(), nullable=False
    )

    op.drop_constraint("ck_documents_project_or_org", "documents", type_="check")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_index("ix_documents_organization_id", table_name="documents")
    op.drop_column("documents", "organization_id")
    op.alter_column("documents", "project_id", existing_type=sa.Integer(), nullable=False)
