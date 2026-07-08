#!/usr/bin/env python
"""
Seed demo dataset with correct schema field names.

Run after alembic upgrade head or after creating schema manually.
"""
import sys
import os
from datetime import datetime, timedelta
import random

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
from app.models.organizations import Organization

CITIES = [
    "Riyadh", "Jeddah", "Dammam", "Medina", "Khobar", "Taif", "Abha",
    "Qassim", "Jubail", "Hafar Al Batin", "Yanbu", "Tabuk", "Buraydah"
]

PROJECT_TYPES = [
    "Residential", "Commercial", "Infrastructure", "Industrial",
    "Healthcare", "Educational", "Hospitality", "Mixed-use"
]

PROJECT_STATUSES = ["Planning", "Active", "Completed", "Delayed", "On Hold"]

MATERIAL_CATEGORIES = [
    "Steel", "Concrete", "Lumber", "HVAC", "Electrical", "Plumbing",
    "Paint", "Doors & Windows", "Roofing", "Insulation", "Tiles"
]

SUPPLIER_CATEGORIES = [
    "Steel Supplier", "Concrete Supplier", "Equipment Rental", "Labor",
    "HVAC Equipment", "Electrical Equipment", "Plumbing Supplies"
]

SUBCONTRACTOR_TRADES = [
    "Concrete Work", "Steel Erection", "Electrical", "Plumbing",
    "HVAC", "Painting", "Carpentry", "Masonry", "Roofing"
]

def random_date(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")

def seed_projects(db, count=60):
    print(f"Seeding {count} projects...")
    base_date = datetime(2023, 1, 1)
    projects = []
    
    for i in range(1, count + 1):
        start = base_date + timedelta(days=random.randint(0, 600))
        planned_finish = start + timedelta(days=random.randint(30, 500))
        
        project = Project(
            project_code=f"PRJ-{i:04d}",
            project_name=f"Construction Project {i}",
            project_type=random.choice(PROJECT_TYPES),
            client_name=f"Client Company {random.randint(1, 30)}",
            city=random.choice(CITIES),
            start_date=start.strftime("%Y-%m-%d"),
            planned_finish=planned_finish.strftime("%Y-%m-%d"),
            status=random.choice(PROJECT_STATUSES),
            budget=random.uniform(500000, 10000000)
        )
        projects.append(project)
        db.add(project)
    
    db.commit()
    print(f"✓ Created {count} projects")
    return projects

def seed_suppliers(db, count=80):
    print(f"Seeding {count} suppliers...")
    suppliers = []
    
    for i in range(1, count + 1):
        supplier = Supplier(
            supplier_name=f"Supplier Company {i}",
            category=random.choice(SUPPLIER_CATEGORIES),
            city=random.choice(CITIES),
            status=random.choice(["Active", "Inactive"])
        )
        suppliers.append(supplier)
        db.add(supplier)
    
    db.commit()
    print(f"✓ Created {count} suppliers")
    return suppliers

def seed_subcontractors(db, count=70):
    print(f"Seeding {count} subcontractors...")
    base_date = datetime(2023, 1, 1)
    subcontractors = []
    
    for i in range(1, count + 1):
        created = base_date + timedelta(days=random.randint(0, 600))
        subcontractor = Subcontractor(
            name=f"Subcontractor Company {i}",
            trade=random.choice(SUBCONTRACTOR_TRADES),
            contact_person=f"Manager {random.randint(1, 100)}",
            phone=f"+966{random.randint(10000000, 99999999)}",
            email=f"sub{i}@contractor.com",
            classification="Grade A",
            city=random.choice(CITIES),
            status="Active",
            created_at=created.strftime("%Y-%m-%d")
        )
        subcontractors.append(subcontractor)
        db.add(subcontractor)
    
    db.commit()
    print(f"✓ Created {count} subcontractors")
    return subcontractors

def seed_purchase_requests(db, projects, count=3000):
    print(f"Seeding {count} purchase requests...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        created = base_date + timedelta(days=random.randint(0, 600))
        
        pr = PurchaseRequest(
            project_id=project.id,
            request_no=f"PR-{i:05d}",
            material_category=random.choice(MATERIAL_CATEGORIES) if random.random() > 0.4 else None,
            specification=f"Spec {i}" if random.random() > 0.35 else None,
            required_delivery_date=(created + timedelta(days=random.randint(7, 60))).strftime("%Y-%m-%d"),
            status=random.choice(["Open", "Approved", "Completed"]),
            created_at=created.strftime("%Y-%m-%d")
        )
        db.add(pr)
    
    db.commit()
    print(f"✓ Created {count} purchase requests")

def seed_purchase_orders(db, projects, suppliers, count=2550):
    print(f"Seeding {count} purchase orders...")
    base_date = datetime(2023, 1, 1)
    
    prs = db.query(PurchaseRequest).all()
    
    for i in range(1, count + 1):
        pr = random.choice(prs) if prs else PurchaseRequest(project_id=random.choice(projects).id, request_no="PR-0000", created_at="2023-01-01", status="Open")
        project = random.choice(projects)
        supplier = random.choice(suppliers)
        issue = base_date + timedelta(days=random.randint(0, 600))
        promised = issue + timedelta(days=random.randint(7, 60))
        
        po = PurchaseOrder(
            pr_id=pr.id if hasattr(pr, 'id') else 1,
            project_id=project.id,
            supplier_id=supplier.id,
            po_number=f"PO-{i:06d}",
            issue_date=issue.strftime("%Y-%m-%d"),
            promised_delivery=promised.strftime("%Y-%m-%d"),
            status=random.choice(["Draft", "Issued", "Received"]),
            is_late=False,
            delay_days=0
        )
        db.add(po)
    
    db.commit()
    print(f"✓ Created {count} purchase orders")

def seed_meetings(db, projects, count=260):
    print(f"Seeding {count} meetings...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        meeting_date = base_date + timedelta(days=random.randint(0, 600))
        
        meeting = Meeting(
            project_id=project.id,
            title=f"Meeting {i}",
            meeting_date=meeting_date.strftime("%Y-%m-%d"),
            meeting_type=random.choice(["Site", "Progress", "Safety", "Planning"])
        )
        db.add(meeting)
    
    db.commit()
    print(f"✓ Created {count} meetings")

def seed_project_decisions(db, projects, count=535):
    print(f"Seeding {count} project decisions...")
    base_date = datetime(2023, 1, 1)
    
    meetings = db.query(Meeting).limit(500).all()
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        meeting = random.choice(meetings) if meetings else None
        decision_date = base_date + timedelta(days=random.randint(0, 600))
        
        if meeting:
            decision = ProjectDecision(
                project_id=project.id,
                meeting_id=meeting.id,
                decision_text=f"Decision {i}",
                decision_date=decision_date.strftime("%Y-%m-%d"),
                owner=f"Manager {random.randint(1, 10)}"
            )
            db.add(decision)
    
    db.commit()
    print(f"✓ Created {count} project decisions")

def seed_site_reports(db, projects, count=1200):
    print(f"Seeding {count} site reports...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        report_date = base_date + timedelta(days=random.randint(0, 600))
        
        report = SiteReport(
            project_id=project.id,
            report_date=report_date.strftime("%Y-%m-%d"),
            weather=random.choice(["Clear", "Cloudy", "Rainy"]),
            summary=f"Daily report for {project.project_name}"
        )
        db.add(report)
    
    db.commit()
    print(f"✓ Created {count} site reports")

def seed_daily_activities(db, projects, subcontractors, count=2385):
    print(f"Seeding {count} daily activities...")
    base_date = datetime(2023, 1, 1)
    
    site_reports = db.query(SiteReport).all()
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        subcontractor = random.choice(subcontractors)  # Required - always assign
        activity_date = base_date + timedelta(days=random.randint(0, 600))
        site_report = random.choice(site_reports) if site_reports else None
        
        if site_report:  # Only create if we have a site report
            activity = DailyActivity(
                project_id=project.id,
                subcontractor_id=subcontractor.id,
                site_report_id=site_report.id,
                activity_date=activity_date.strftime("%Y-%m-%d"),
                activity_description=f"Activity {i}",
                manpower_count=random.randint(5, 50)
            )
            db.add(activity)
    
    db.commit()
    print(f"✓ Created {count} daily activities")

def seed_documents(db, projects, count=120):
    print(f"Seeding {count} documents...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        doc_date = base_date + timedelta(days=random.randint(0, 600))
        
        doc = Document(
            project_id=project.id,
            doc_type=random.choice(["Contract", "Drawing", "Report"]),
            title=f"Document {i}",
            doc_date=doc_date.strftime("%Y-%m-%d"),
            content_summary=f"Content for doc {i}"
        )
        db.add(doc)
    
    db.commit()
    print(f"✓ Created {count} documents")

def seed_generated_documents(db, projects, count=1060):
    print(f"Seeding {count} generated documents...")
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        
        gen_doc = GeneratedDocument(
            file_name=f"Report_{i}.pdf",
            type="Analysis",
            project_id=project.id,
            related_record_id=project.id,  # Required - use project id
            document_date="2025-01-01",
            sender="System",
            recipient="Admin",
            subject=f"Generated Report {i}",
            body=f"Content for report {i}"
        )
        db.add(gen_doc)
    
    db.commit()
    print(f"✓ Created {count} generated documents")

def seed_correspondence(db, projects, count=120):
    print(f"Seeding {count} correspondence...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        sent_date = base_date + timedelta(days=random.randint(0, 600))
        
        corr = Correspondence(
            project_id=project.id,
            related_record_type="Project",
            related_record_id=project.id,
            sent_date=sent_date.strftime("%Y-%m-%d"),
            sender="Sender",
            recipient="Recipient",
            subject=f"Subject {i}",
            body=f"Body text for message {i}"
        )
        db.add(corr)
    
    db.commit()
    print(f"✓ Created {count} correspondence")

def seed_safety_events(db, projects, subcontractors, count=449):
    print(f"Seeding {count} safety events...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        subcontractor = random.choice(subcontractors)  # Required - always assign
        event_date = base_date + timedelta(days=random.randint(0, 600))
        
        event = SafetyEvent(
            project_id=project.id,
            subcontractor_id=subcontractor.id,
            event_date=event_date.strftime("%Y-%m-%d"),
            severity=random.choice(["Low", "Medium", "High"]),
            description=f"Safety incident {i}",
            corrective_action="Action taken"
        )
        db.add(event)
    
    db.commit()
    print(f"✓ Created {count} safety events")

def seed_ncrs(db, projects, suppliers, subcontractors, count=739):
    print(f"Seeding {count} NCRs...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        supplier = random.choice(suppliers) if random.random() > 0.3 else None
        subcontractor = random.choice(subcontractors) if random.random() > 0.3 else None
        issue_date = base_date + timedelta(days=random.randint(0, 600))
        
        ncr = NCR(
            project_id=project.id,
            supplier_id=supplier.id if supplier else None,
            subcontractor_id=subcontractor.id if subcontractor else None,
            ncr_type="Quality",
            description=f"NCR {i}",
            root_cause="Root cause",
            issue_date=issue_date.strftime("%Y-%m-%d"),
            status=random.choice(["Open", "Closed"])
        )
        db.add(ncr)
    
    db.commit()
    print(f"✓ Created {count} NCRs")

def seed_claims(db, projects, count=120):
    print(f"Seeding {count} claims...")
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        
        claim = Claim(
            project_id=project.id,
            claim_number=f"CLM-{i:05d}",
            claim_type="Cost",
            amount=random.uniform(10000, 500000),
            status=random.choice(["Submitted", "Approved"]),
            narrative=f"Claim narrative {i}"
        )
        db.add(claim)
    
    db.commit()
    print(f"✓ Created {count} claims")

def seed_change_orders(db, projects, count=120):
    print(f"Seeding {count} change orders...")
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        
        co = ChangeOrder(
            project_id=project.id,
            co_number=f"CO-{i:06d}",
            description=f"Change order {i}",
            value=random.uniform(-100000, 200000),
            status="Approved"
        )
        db.add(co)
    
    db.commit()
    print(f"✓ Created {count} change orders")

def seed_subcontractor_evaluations(db, projects, subcontractors, count=499):
    print(f"Seeding {count} subcontractor evaluations...")
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        subcontractor = random.choice(subcontractors)
        
        eval = SubcontractorEvaluation(
            project_id=project.id,
            subcontractor_id=subcontractor.id,
            evaluation_date="2025-01-01",
            quality_score=random.randint(1, 10),
            safety_score=random.randint(1, 10),
            schedule_score=random.randint(1, 10),
            manpower_score=random.randint(1, 10),
            overall_rating=random.uniform(5, 10),
            comments="Evaluation comment"
        )
        db.add(eval)
    
    db.commit()
    print(f"✓ Created {count} subcontractor evaluations")

def seed_claim_evidence(db, count=120):
    print(f"Seeding {count} claim evidence...")
    
    claims = db.query(Claim).all()
    change_orders = db.query(ChangeOrder).all()
    decisions = db.query(ProjectDecision).all()
    documents = db.query(Document).all()
    correspondences = db.query(Correspondence).all()
    
    for i in range(1, count + 1):
        if claims and change_orders and decisions and documents and correspondences:
            claim = random.choice(claims)
            co = random.choice(change_orders)
            decision = random.choice(decisions)
            doc = random.choice(documents)
            corr = random.choice(correspondences)
            
            evidence = ClaimEvidence(
                claim_id=claim.id,
                change_order_id=co.id,
                decision_id=decision.id,
                document_id=doc.id,
                correspondence_id=corr.id,
                evidence_note=f"Evidence {i}"
            )
            db.add(evidence)
    
    db.commit()
    print(f"✓ Created {count} claim evidence")

def run():
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("SEEDING DEMO DATASET")
        print("="*60 + "\n")
        
        org = db.query(Organization).filter(Organization.slug == "amad-demo").first()
        if not org:
            org = Organization(name="Amad Demo", slug="amad-demo", is_active=True)
            db.add(org)
            db.commit()
        
        projects = seed_projects(db, 60)
        suppliers = seed_suppliers(db, 80)
        subcontractors = seed_subcontractors(db, 70)
        seed_meetings(db, projects, 260)
        seed_project_decisions(db, projects, 535)
        seed_purchase_requests(db, projects, 3000)
        seed_purchase_orders(db, projects, suppliers, 2550)
        seed_site_reports(db, projects, 1200)
        seed_daily_activities(db, projects, subcontractors, 2385)
        seed_documents(db, projects, 120)
        seed_generated_documents(db, projects, 1060)
        seed_correspondence(db, projects, 120)
        seed_safety_events(db, projects, subcontractors, 449)
        seed_ncrs(db, projects, suppliers, subcontractors, 739)
        seed_claims(db, projects, 120)
        seed_change_orders(db, projects, 120)
        seed_subcontractor_evaluations(db, projects, subcontractors, 499)
        seed_claim_evidence(db, 120)
        
        print("\n" + "="*60)
        print("✓ SEEDING COMPLETE")
        print("="*60)
        
    finally:
        db.close()


if __name__ == "__main__":
    run()
