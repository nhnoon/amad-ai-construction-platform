from pydantic import BaseModel
from typing import Optional


class SupplierOut(BaseModel):
    id: int
    supplier_name: str
    category: str
    city: str
    status: str

    model_config = {"from_attributes": True}


class PurchaseRequestBase(BaseModel):
    project_id: int
    request_no: str
    material_category: Optional[str] = None
    specification: Optional[str] = None
    required_delivery_date: Optional[str] = None
    status: str
    rework_reason: Optional[str] = None
    created_at: str


class PurchaseRequestCreate(PurchaseRequestBase):
    pass


class PurchaseRequestOut(PurchaseRequestBase):
    id: int

    model_config = {"from_attributes": True}


class PurchaseOrderOut(BaseModel):
    id: int
    pr_id: int
    project_id: int
    supplier_id: int
    po_number: str
    issue_date: str
    promised_delivery: str
    actual_delivery: Optional[str] = None
    status: str
    is_late: bool
    delay_days: int
    delay_root_cause: Optional[str] = None

    model_config = {"from_attributes": True}
