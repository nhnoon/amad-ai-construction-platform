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

Not yet read or written by app/ai/pipeline.py — see that module's docstring
for the retrieval/generation flow these tables are deliberately excluded
from for now.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
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
