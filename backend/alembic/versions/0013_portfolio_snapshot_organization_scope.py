"""Phase 1 production-hardening — scope portfolio_score_snapshots per
organization.

The table was previously global: one row per calendar date, uniquely keyed
on snapshot_date alone. Once Executive Intelligence (app/api/v1/executive.py)
is computed per-organization, two organizations recomputing intelligence on
the same day would overwrite each other's snapshot for that date under the
old unique constraint, and the Portfolio Trend chart would silently mix
history from more than one organization. This migration adds
organization_id, backfills any existing rows (verified at authoring time:
exactly 1 row, "today's" snapshot, written by the pre-Phase-1 unscoped
code path) onto the sole existing organization using the same
"refuse to guess if ambiguous" guard as 0012, and re-keys uniqueness to
(snapshot_date, organization_id).

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-19
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sole_organization_id(bind) -> int:
    org_count = bind.execute(sa.text("SELECT COUNT(*) FROM organizations")).scalar()
    if org_count != 1:
        raise RuntimeError(
            f"Refusing to backfill: expected exactly 1 organization for an "
            f"unambiguous backfill, found {org_count}. Assign "
            f"organization_id manually for the affected "
            f"portfolio_score_snapshots rows, then re-run this migration."
        )
    return bind.execute(sa.text("SELECT id FROM organizations LIMIT 1")).scalar()


def upgrade() -> None:
    bind = op.get_bind()

    op.drop_constraint(
        "uq_portfolio_score_snapshots_date", "portfolio_score_snapshots", type_="unique"
    )
    op.add_column(
        "portfolio_score_snapshots",
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )

    unassigned = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM portfolio_score_snapshots WHERE organization_id IS NULL"
        )
    ).scalar()
    if unassigned and unassigned > 0:
        sole_org_id = _sole_organization_id(bind)
        bind.execute(
            sa.text(
                "UPDATE portfolio_score_snapshots SET organization_id = :org_id "
                "WHERE organization_id IS NULL"
            ),
            {"org_id": sole_org_id},
        )

    op.alter_column("portfolio_score_snapshots", "organization_id", nullable=False)
    op.create_index(
        "ix_portfolio_score_snapshots_organization_id",
        "portfolio_score_snapshots", ["organization_id"],
    )
    op.create_foreign_key(
        "fk_portfolio_score_snapshots_organization_id_organizations",
        "portfolio_score_snapshots", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_portfolio_score_snapshots_date_org",
        "portfolio_score_snapshots", ["snapshot_date", "organization_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_portfolio_score_snapshots_date_org", "portfolio_score_snapshots", type_="unique"
    )
    op.drop_constraint(
        "fk_portfolio_score_snapshots_organization_id_organizations",
        "portfolio_score_snapshots", type_="foreignkey",
    )
    op.drop_index(
        "ix_portfolio_score_snapshots_organization_id", table_name="portfolio_score_snapshots"
    )
    op.drop_column("portfolio_score_snapshots", "organization_id")
    op.create_unique_constraint(
        "uq_portfolio_score_snapshots_date", "portfolio_score_snapshots", ["snapshot_date"]
    )
