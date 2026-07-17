"""Copilot Memory Layer — bounded, user-scoped agent memory.

Design (inspired by Hermes Agent's own memory model — see
``hermes config path`` / ``memory.memory_char_limit`` / ``memory.user_char_limit``
in a local Hermes install): Hermes keeps exactly two bounded, plain-text
stores per profile — USER.md (user preferences/profile) and MEMORY.md
(derived notes) — both capped by a character limit, never a dump of raw
tool output. This mirrors that split as two Postgres tables instead of
files, scoped per AMAD user rather than per Hermes profile:

  * ``AIUserProfileMemory`` — one bounded row per user: durable preferences
    /working style (e.g. "prefers Arabic answers"). Analogous to USER.md.
  * ``AIMemoryNote``        — one bounded row per user: short derived notes
    accumulated across conversations. Analogous to MEMORY.md.

Both are intentionally NOT a cache of retrieved evidence or project
records — PostgreSQL's existing domain tables remain the sole source of
truth for that data. Enforcement of the character bound and of the "no
evidence dumps" rule lives in the service layer (app/ai/memory.py), not
here; these are plain bounded-text rows.

Read and written by app/ai/pipeline.py as of the Knowledge Access Layer /
Memory Completion work — see app/ai/memory.py (read/write service layer)
and app/ai/memory_reader.py (relevance/ranking) for how these two tables
reach the Hermes prompt. AIMemoryRecord below is the third table in this
module: a structured, one-row-per-memory store (distinct from the two
bounded per-user blobs above) — see its own docstring.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, UniqueConstraint, Index
from sqlalchemy.sql import func
from .base import Base


class AIUserProfileMemory(Base):
    """Bounded, durable per-user preferences (analogous to Hermes's USER.md)."""

    __tablename__ = "ai_user_profile_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Denormalized snapshot, matching the pattern already used on
    # ai_conversations — convenient for audit/reporting queries.
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    content = Column(Text, nullable=False, default="")
    char_limit = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_ai_user_profile_memory_user_id"),
    )


class AIMemoryNote(Base):
    """Bounded, derived per-user notes (analogous to Hermes's MEMORY.md).

    Never a copy of retrieval evidence — see app/ai/memory.py for the write
    guard that rejects evidence-shaped content.
    """

    __tablename__ = "ai_memory_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    content = Column(Text, nullable=False, default="")
    char_limit = Column(Integer, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_ai_memory_notes_user_id"),
    )


class AIMemoryRecord(Base):
    """One structured memory per row — the durable, cross-conversation
    knowledge store distinct from the two bounded per-user blobs above.

    Where AIMemoryNote/AIUserProfileMemory are Hermes-USER.md/MEMORY.md-
    style bounded text (one row per user, notes packed as lines), this
    table is a real queryable record per important AI interaction —
    meeting summary, risk report, site report analysis, contract analysis,
    executive summary, decision, action item, etc. — searchable by
    project, category, and keyword, and citable by evidence code. See
    app/ai/memory_records.py for the write/search service layer.
    """

    __tablename__ = "ai_memory_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Creator, for audit — NOT the isolation boundary (see organization_id/
    # project_id below); unlike AIMemoryNote/AIUserProfileMemory, memory
    # records are shared knowledge across a project's/organization's team,
    # not private to the user who triggered the write.
    user_id = Column(
        Integer,
        ForeignKey("user_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    # What kind of AI interaction produced this memory — e.g. "meeting",
    # "site_report", "contract_extraction", "decision", "action_item".
    source = Column(String(50), nullable=False)
    # Coarser grouping for filtering/search — e.g. "meeting_summary",
    # "risk_report", "supplier_analysis", "executive_summary".
    category = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    # Comma-separated keyword list — kept as plain text (not JSONB/ARRAY)
    # for portability and to match the simple substring-match ranking
    # already used by memory_reader.py's select_relevant_memory().
    keywords = Column(Text, nullable=False, default="")
    # 0-100 — how much the writer trusts this memory (deterministic
    # writers use a fixed high value; anything derived from an LLM pass
    # should carry that call's own confidence signal, never a fabricated
    # one). NOT the same axis as the risk score.
    confidence = Column(Integer, nullable=False, default=100)
    # Evidence code the memory can be cited back to (e.g. "MTG-1", "SR-42",
    # "DEC-7") — lets Hermes cite historical memory the same way it cites
    # live evidence, per the ticket's citation requirement.
    citation = Column(String(50), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_ai_memory_records_org_project", "organization_id", "project_id"),
        Index("ix_ai_memory_records_category", "category"),
    )
