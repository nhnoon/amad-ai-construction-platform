#!/usr/bin/env python
"""
Verify demo dataset row counts.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.projects import Project
from app.models.procurement import Supplier, PurchaseRequest, PurchaseOrder
from app.models.meetings import Meeting, ProjectDecision
from app.models.site import SiteReport, DailyActivity
from app.models.documents import Document, GeneratedDocument, Correspondence
from app.models.safety import SafetyEvent, NCR
from app.models.claims import Claim, ChangeOrder, ClaimEvidence
from app.models.subcontractors import Subcontractor, SubcontractorEvaluation

db = SessionLocal()

print("\n" + "="*60)
print("DATA TABLE ROW COUNTS")
print("="*60)

tables = [
    ("Projects", Project),
    ("Suppliers", Supplier),
    ("Subcontractors", Subcontractor),
    ("Meetings", Meeting),
    ("Project Decisions", ProjectDecision),
    ("Purchase Requests", PurchaseRequest),
    ("Purchase Orders", PurchaseOrder),
    ("Site Reports", SiteReport),
    ("Daily Activities", DailyActivity),
    ("Documents", Document),
    ("Generated Documents", GeneratedDocument),
    ("Correspondence", Correspondence),
    ("Safety Events", SafetyEvent),
    ("NCRs", NCR),
    ("Claims", Claim),
    ("Change Orders", ChangeOrder),
    ("Subcontractor Evaluations", SubcontractorEvaluation),
    ("Claim Evidence", ClaimEvidence),
]

total = 0
for name, model in tables:
    count = db.query(model).count()
    print(f"  {name:.<40} {count:>6} rows")
    total += count

print("="*60)
print(f"  {'TOTAL':.<40} {total:>6} rows")
print("="*60 + "\n")

db.close()
