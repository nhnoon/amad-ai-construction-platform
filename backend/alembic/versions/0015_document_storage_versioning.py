"""Add Document Storage System: persistent, versioned file storage

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-01

Adds a current-version snapshot to `documents` (all nullable/defaulted —
every existing row, created before this migration and never having gone
through the new upload/versioning path, continues to read back exactly as
before with these fields simply NULL/false) and a new append-only
`document_versions` history table. No existing column is altered, dropped,
or renamed; no existing row's data changes. See app/models/documents.py
for the ORM-level definitions this mirrors and app/ai/document_storage.py
for what populates them.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("storage_key", sa.String(500), nullable=True))
    op.add_column("documents", sa.Column("original_filename", sa.String(255), nullable=True))
    op.add_column("documents", sa.Column("mime_type", sa.String(100), nullable=True))
    op.add_column("documents", sa.Column("file_size", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("checksum", sa.String(64), nullable=True))
    op.add_column("documents", sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("uploaded_by", sa.Integer(), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column("documents", sa.Column("version_number", sa.Integer(), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_foreign_key(
        "fk_documents_uploaded_by_user_accounts", "documents", "user_accounts",
        ["uploaded_by"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_documents_checksum", "documents", ["checksum"])
    op.create_index("ix_documents_is_archived", "documents", ["is_archived"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id", sa.Integer(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("storage_provider", sa.String(20), nullable=False, server_default="local"),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "uploaded_by", sa.Integer(),
            sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.UniqueConstraint(
            "document_id", "version_number",
            name="uq_document_versions_document_id_version_number",
        ),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("ix_document_versions_checksum", "document_versions", ["checksum"])


def downgrade() -> None:
    op.drop_index("ix_document_versions_checksum", table_name="document_versions")
    op.drop_index("ix_document_versions_document_id", table_name="document_versions")
    op.drop_table("document_versions")

    op.drop_index("ix_documents_is_archived", table_name="documents")
    op.drop_index("ix_documents_checksum", table_name="documents")
    op.drop_constraint("fk_documents_uploaded_by_user_accounts", "documents", type_="foreignkey")
    op.drop_column("documents", "is_archived")
    op.drop_column("documents", "version_number")
    op.drop_column("documents", "updated_at")
    op.drop_column("documents", "uploaded_by")
    op.drop_column("documents", "uploaded_at")
    op.drop_column("documents", "checksum")
    op.drop_column("documents", "file_size")
    op.drop_column("documents", "mime_type")
    op.drop_column("documents", "original_filename")
    op.drop_column("documents", "storage_key")
