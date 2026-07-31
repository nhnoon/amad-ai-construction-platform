"""Add PortfolioScoreSnapshot: daily portfolio score history for the
Executive Dashboard's trend chart

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-19
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolio_score_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("portfolio_score", sa.Integer(), nullable=False),
        sa.Column("portfolio_status", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("snapshot_date", name="uq_portfolio_score_snapshots_date"),
    )


def downgrade() -> None:
    op.drop_table("portfolio_score_snapshots")
