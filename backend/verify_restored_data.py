#!/usr/bin/env python
"""Verify restored data with table counts and sample names."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.projects import Project
from app.models.procurement import Supplier, PurchaseOrder, PurchaseRequest
from app.models.meetings import Meeting, ProjectDecision
from app.models.site import SiteReport, DailyActivity
from app.models.documents import Document, GeneratedDocument, Correspondence
from app.models.safety import SafetyEvent, NCR
from app.models.claims import Claim, ChangeOrder, ClaimEvidence
from app.models.subcontractors import Subcontractor, SubcontractorEvaluation

db = SessionLocal()

print("\n" + "="*70)
print("RESTORED ORIGINAL DATA VERIFICATION")
print("="*70)

# Count all tables
tables = {
    "projects": (Project, db.query(Project).count()),
    "suppliers": (Supplier, db.query(Supplier).count()),
    "subcontractors": (Subcontractor, db.query(Subcontractor).count()),
    "meetings": (Meeting, db.query(Meeting).count()),
    "project_decisions": (ProjectDecision, db.query(ProjectDecision).count()),
    "purchase_requests": (PurchaseRequest, db.query(PurchaseRequest).count()),
    "purchase_orders": (PurchaseOrder, db.query(PurchaseOrder).count()),
    "site_reports": (SiteReport, db.query(SiteReport).count()),
    "daily_activities": (DailyActivity, db.query(DailyActivity).count()),
    "documents": (Document, db.query(Document).count()),
    "generated_documents": (GeneratedDocument, db.query(GeneratedDocument).count()),
    "correspondence": (Correspondence, db.query(Correspondence).count()),
    "safety_events": (SafetyEvent, db.query(SafetyEvent).count()),
    "ncrs": (NCR, db.query(NCR).count()),
    "claims": (Claim, db.query(Claim).count()),
    "change_orders": (ChangeOrder, db.query(ChangeOrder).count()),
    "subcontractor_evaluations": (SubcontractorEvaluation, db.query(SubcontractorEvaluation).count()),
    "claim_evidence": (ClaimEvidence, db.query(ClaimEvidence).count()),
}

print("\nTABLE COUNTS:")
print("-" * 70)
total = 0
for table_name, (_, count) in sorted(tables.items()):
    print(f"  {table_name:<35} {count:>6}")
    total += count

print("-" * 70)
print(f"  {'TOTAL':<35} {total:>6}")

# Sample data
print("\n" + "="*70)
print("SAMPLE DATA (Verifying Original Dataset)")
print("="*70)

print("\nProjects (first 3):")
for p in db.query(Project).limit(3).all():
    print(f"  {p.project_name:30} | {p.project_code} | Budget: {p.budget:,.0f}")

print("\nSuppliers (first 3):")
for s in db.query(Supplier).limit(3).all():
    print(f"  {s.supplier_name:30} | {s.category}")

print("\nSubcontractors (first 3):")
for sc in db.query(Subcontractor).limit(3).all():
    print(f"  {sc.name:30} | {sc.trade}")

print("\nMeetings (first 3):")
for m in db.query(Meeting).limit(3).all():
    print(f"  Meeting {m.id:3} | Project {m.project_id:2} | {m.meeting_date}")

print("\n" + "="*70)
print("✓ DATA RESTORATION VERIFICATION COMPLETE")
print("="*70 + "\n")

db.close()
