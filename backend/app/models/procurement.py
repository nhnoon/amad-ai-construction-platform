from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .base import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)

    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    ncrs = relationship("NCR", back_populates="supplier")


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    request_no = Column(String(50), nullable=False)
    material_category = Column(String(100), nullable=True)
    specification = Column(Text, nullable=True)
    required_delivery_date = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, index=True)
    rework_reason = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False)

    project = relationship("Project", back_populates="purchase_requests")
    purchase_orders = relationship("PurchaseOrder", back_populates="purchase_request")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_id = Column(Integer, ForeignKey("purchase_requests.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    po_number = Column(String(50), nullable=False)
    issue_date = Column(String(50), nullable=False)
    promised_delivery = Column(String(50), nullable=False)
    actual_delivery = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False)
    is_late = Column(Boolean, nullable=False, default=False, index=True)
    delay_days = Column(Integer, nullable=False, default=0)
    delay_root_cause = Column(Text, nullable=True)

    purchase_request = relationship("PurchaseRequest", back_populates="purchase_orders")
    project = relationship("Project", back_populates="purchase_orders")
    supplier = relationship("Supplier", back_populates="purchase_orders")
