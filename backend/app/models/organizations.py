from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint, ForeignKeyConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users = relationship("UserAccount", back_populates="organization")

    __table_args__ = (
        Index("ix_organizations_slug", "slug", unique=True),
    )


class ProjectMembership(Base):
    __tablename__ = "project_memberships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=False)
    role_on_project = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("UserAccount", back_populates="memberships")
    project = relationship("Project", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_project_membership"),
        ForeignKeyConstraint(
            ["user_id"],
            ["user_accounts.id"],
            name="fk_project_memberships_user_id_user_accounts",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_project_memberships_project_id_projects",
            ondelete="CASCADE",
        ),
        Index("ix_project_memberships_user_id", "user_id"),
        Index("ix_project_memberships_project_id", "project_id"),
    )
