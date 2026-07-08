from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class ChangeOrder(Base):
    __tablename__ = "change_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    co_number = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)

    project = relationship("Project", back_populates="change_orders")
    claim_evidence = relationship("ClaimEvidence", back_populates="change_order")


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    claim_number = Column(String(50), nullable=False)
    claim_type = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)
    narrative = Column(Text, nullable=False)

    project = relationship("Project", back_populates="claims")
    evidence = relationship("ClaimEvidence", back_populates="claim")


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    change_order_id = Column(Integer, ForeignKey("change_orders.id"), nullable=False)
    decision_id = Column(Integer, ForeignKey("project_decisions.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    correspondence_id = Column(Integer, ForeignKey("correspondence.id"), nullable=False)
    evidence_note = Column(Text, nullable=False)

    claim = relationship("Claim", back_populates="evidence")
    change_order = relationship("ChangeOrder", back_populates="claim_evidence")
    decision = relationship("ProjectDecision", back_populates="claim_evidence")
    document = relationship("Document", back_populates="claim_evidence")
    correspondence = relationship("Correspondence", back_populates="claim_evidence")
