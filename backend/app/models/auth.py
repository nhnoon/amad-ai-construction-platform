from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="viewer")
    is_active = Column(Boolean, nullable=False, default=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    # Phase 2 — Security & Authentication Hardening (see migration 0014).
    # Defaults to False so existing users are never retroactively forced
    # into this flow — application code (register/admin-create-user)
    # explicitly sets it True for newly provisioned accounts only.
    must_change_password = Column(Boolean, nullable=False, default=False)
    failed_login_attempts = Column(Integer, nullable=False, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="users")
    memberships = relationship("ProjectMembership", back_populates="user")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_user_accounts_org_id", "organization_id"),
    )


class RefreshToken(Base):
    """RC1 Phase 1 Sprint 1 — Identity & Session Security.

    One row per issued refresh token; also doubles as this app's session
    record (GET /auth/sessions lists the currently-active rows verbatim).
    Rotation-on-use: a successful POST /auth/refresh revokes this row
    (revoked_at) and inserts a new row sharing the same family_id — see
    app/core/session_security.py for the rotation/reuse-detection logic
    that owns every write to this table. token_hash stores SHA-256 of the
    opaque random token, never the raw token itself, so a database
    compromise alone cannot be used to mint requests as a live session.
    """

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(64), nullable=False)
    # Shared by every token in one rotation chain — the stable identifier
    # for "one logical session" across however many times it has rotated.
    family_id = Column(String(32), nullable=False)
    remember_me = Column(Boolean, nullable=False, default=False)
    device = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("UserAccount", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_token_hash", "token_hash", unique=True),
        Index("ix_refresh_tokens_family_id", "family_id"),
    )
