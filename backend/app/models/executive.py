"""Portfolio score history — one row per (day, organization), upserted as a
side effect each time executive intelligence is (re)computed (see
app/api/v1/executive.py::_compute_executive_intelligence). Before this,
portfolio_score was a snapshot-only value with no history anywhere, so the
Executive Dashboard's trend chart had nothing to chart. There is no
cron/scheduler in this app — history simply starts accumulating from
whichever day this table first gets written to, not from any earlier date.
Scoped per-organization (Phase 1 production-hardening) so two organizations
computing intelligence the same day don't overwrite each other's snapshot
and the trend chart never mixes another organization's history in.
"""
from sqlalchemy import Column, ForeignKey, Integer, String, Date, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from .base import Base


class PortfolioScoreSnapshot(Base):
    __tablename__ = "portfolio_score_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(Date, nullable=False)
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    portfolio_score = Column(Integer, nullable=False)
    portfolio_status = Column(String(20), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "snapshot_date", "organization_id",
            name="uq_portfolio_score_snapshots_date_org",
        ),
    )
