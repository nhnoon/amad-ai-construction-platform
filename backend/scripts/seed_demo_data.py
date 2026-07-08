#!/usr/bin/env python
"""
Generate comprehensive demo dataset to match Replit live environment.

Run after alembic upgrade head:
    cd backend && python -m scripts.seed_demo_data

Expected row counts:
- projects: 60
- suppliers: 80
- subcontractors: 70
- meetings: 260
- project_decisions: 535
- purchase_requests: 3,000
- purchase_orders: 2,550
- site_reports: 1,200
- daily_activities: 2,385
- documents: 120
- generated_documents: 1,060
- correspondence: 120
- safety_events: 449
- ncrs: 739
- claims: 120
- change_orders: 120
- subcontractor_evaluations: 499
- claim_evidence: 120
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

# Saudi cities
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
    "Paint", "Doors & Windows", "Roofing", "Insulation", "Tiles",
    "Glass", "Hardware", "Safety Equipment"
]

SUPPLIER_CATEGORIES = [
    "Steel Supplier", "Concrete Supplier", "Equipment Rental", "Labor",
    "HVAC Equipment", "Electrical Equipment", "Plumbing Supplies",
    "Paint Supplier", "Building Materials", "Safety Equipment"
]

SUBCONTRACTOR_TRADES = [
    "Concrete Work", "Steel Erection", "Electrical", "Plumbing",
    "HVAC", "Painting", "Carpentry", "Masonry", "Roofing",
    "Excavation", "Piling", "Scaffolding"
]

CLASSIFICATIONS = [
    "Grade A", "Grade B", "Grade C", "Specialized"
]

def random_date(start_date, end_date):
    """Generate random date between two dates"""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")

def seed_projects(db, count=60):
    """Seed projects"""
    print(f"Seeding {count} projects...")
    base_date = datetime(2023, 1, 1)
    projects = []
    
    for i in range(1, count + 1):
        start = base_date + timedelta(days=random.randint(0, 600))
        planned_finish = start + timedelta(days=random.randint(30, 500))
        actual_finish = None
        status = random.choice(PROJECT_STATUSES)
        if status == "Completed":
            actual_finish = random_date(start, planned_finish).split()[0] if random_date(start, planned_finish) else None
        
        project = Project(
            project_code=f"PRJ-{i:04d}",
            project_name=f"Construction Project {i}",
            project_type=random.choice(PROJECT_TYPES),
            client_name=f"Client Company {random.randint(1, 30)}",
            city=random.choice(CITIES),
            start_date=start.strftime("%Y-%m-%d"),
            planned_finish=planned_finish.strftime("%Y-%m-%d"),
            actual_finish=actual_finish,
            status=status,
            budget=random.uniform(500000, 10000000)
        )
        projects.append(project)
        db.add(project)
    
    db.commit()
    print(f"✓ Created {count} projects")
    return projects

def seed_suppliers(db, count=80):
    """Seed suppliers"""
    print(f"Seeding {count} suppliers...")
    suppliers = []
    
    for i in range(1, count + 1):
        supplier = Supplier(
            supplier_name=f"Supplier Company {i}",
            category=random.choice(SUPPLIER_CATEGORIES),
            city=random.choice(CITIES),
            status=random.choice(["Active", "Inactive", "Suspended"])
        )
        suppliers.append(supplier)
        db.add(supplier)
    
    db.commit()
    print(f"✓ Created {count} suppliers")
    return suppliers

def seed_subcontractors(db, count=70):
    """Seed subcontractors"""
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
            classification=random.choice(CLASSIFICATIONS),
            city=random.choice(CITIES),
            status=random.choice(["Active", "Inactive"]),
            created_at=created.strftime("%Y-%m-%d")
        )
        subcontractors.append(subcontractor)
        db.add(subcontractor)
    
    db.commit()
    print(f"✓ Created {count} subcontractors")
    return subcontractors

def seed_purchase_requests(db, projects, count=3000):
    """Seed purchase requests"""
    print(f"Seeding {count} purchase requests...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        created = base_date + timedelta(days=random.randint(0, 600))
        
        purchase_request = PurchaseRequest(
            project_id=project.id,
            request_no=f"PR-{i:05d}",
            material_category=random.choice(MATERIAL_CATEGORIES) if random.random() > 0.4 else None,
            specification=f"Specification for item {i}" if random.random() > 0.35 else None,
            required_delivery_date=(created + timedelta(days=random.randint(7, 60))).strftime("%Y-%m-%d"),
            status=random.choice(["Open", "Approved", "Completed", "Cancelled"]),
            created_at=created.strftime("%Y-%m-%d")
        )
        db.add(purchase_request)
    
    db.commit()
    print(f"✓ Created {count} purchase requests")

def seed_purchase_orders(db, projects, suppliers, count=2550):
    """Seed purchase orders"""
    print(f"Seeding {count} purchase orders...")
    base_date = datetime(2023, 1, 1)
    
    # Get purchase requests
    db_session = SessionLocal()
    purchase_requests = db_session.query(PurchaseRequest).all()
    db_session.close()
    
    for i in range(1, count + 1):
        pr = random.choice(purchase_requests)
        project = pr.project
        supplier = random.choice(suppliers)
        issue = base_date + timedelta(days=random.randint(0, 600))
        promised = issue + timedelta(days=random.randint(7, 60))
        actual = None
        is_late = False
        delay_days = 0
        
        if random.random() > 0.3:
            actual = issue + timedelta(days=random.randint(7, 90))
            if actual > promised:
                is_late = True
                delay_days = (actual - promised).days
        
        purchase_order = PurchaseOrder(
            pr_id=pr.id,
            project_id=project.id,
            supplier_id=supplier.id,
            po_number=f"PO-{i:06d}",
            issue_date=issue.strftime("%Y-%m-%d"),
            promised_delivery=promised.strftime("%Y-%m-%d"),
            actual_delivery=actual.strftime("%Y-%m-%d") if actual else None,
            status=random.choice(["Draft", "Issued", "Received", "Completed"]),
            is_late=is_late,
            delay_days=delay_days,
            delay_root_cause="Supplier delay" if is_late and random.random() > 0.5 else None
        )
        db.add(purchase_order)
    
    db.commit()
    print(f"✓ Created {count} purchase orders")

def seed_meetings(db, projects, count=260):
    """Seed meetings"""
    print(f"Seeding {count} meetings...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        meeting_date = base_date + timedelta(days=random.randint(0, 600))
        
        meeting = Meeting(
            project_id=project.id,
            title=f"Project Meeting {i}",
            meeting_date=meeting_date.strftime("%Y-%m-%d"),
            meeting_type=random.choice(["Site", "Progress", "Safety", "Planning", "Review"])
        )
        db.add(meeting)
    
    db.commit()
    print(f"✓ Created {count} meetings")

def seed_project_decisions(db, projects, count=535):
    """Seed project decisions"""
    print(f"Seeding {count} project decisions...")
    base_date = datetime(2023, 1, 1)
    
    # Get meetings
    db_session = SessionLocal()
    meetings = db_session.query(Meeting).all()
    db_session.close()
    
    if not meetings:
        print("  WARNING: No meetings found - creating minimal meetings for decisions")
        # Create some meetings first
        for p in projects[:10]:
            m = Meeting(
                project_id=p.id,
                title=f"Meeting for decisions",
                meeting_date=base_date.strftime("%Y-%m-%d"),
                meeting_type="Planning"
            )
            db.add(m)
        db.commit()
        db_session = SessionLocal()
        meetings = db_session.query(Meeting).all()
        db_session.close()
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        decision_date = base_date + timedelta(days=random.randint(0, 600))
        meeting = random.choice(meetings)
        
        decision = ProjectDecision(
            project_id=project.id,
            meeting_id=meeting.id,
            decision_text=f"Decision {i}: {random.choice(['Approved', 'Deferred', 'Rejected', 'Modified'])} {random.choice(['design change', 'timeline adjustment', 'scope modification', 'budget adjustment'])}",
            decision_date=decision_date.strftime("%Y-%m-%d"),
            owner=f"Project Manager {random.randint(1, 10)}"
        )
        db.add(decision)
    
    db.commit()
    print(f"✓ Created {count} project decisions")

def seed_site_reports(db, projects, count=1200):
    """Seed site reports"""
    print(f"Seeding {count} site reports...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        report_date = base_date + timedelta(days=random.randint(0, 600))
        
        site_report = SiteReport(
            project_id=project.id,
            report_date=report_date.strftime("%Y-%m-%d"),
            report_type=random.choice(["Daily", "Weekly", "Monthly", "Phase Completion"]),
            site_manager=f"Site Manager {random.randint(1, 20)}",
            weather=random.choice(["Clear", "Cloudy", "Rainy", "Windy", "Hot"]),
            workers_on_site=random.randint(10, 100),
            equipment_status=random.choice(["Operational", "Partial", "Limited"]),
            progress_percentage=random.randint(0, 100),
            summary=f"Site progress report for {project.project_name}. Various activities ongoing.",
            issues=f"Issue {random.randint(1, 5)}: {random.choice(['Material delay', 'Equipment issue', 'Weather impact', 'Labor shortage'])}" if random.random() > 0.5 else None
        )
        db.add(site_report)
    
    db.commit()
    print(f"✓ Created {count} site reports")

def seed_daily_activities(db, projects, subcontractors, count=2385):
    """Seed daily activities"""
    print(f"Seeding {count} daily activities...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        subcontractor = random.choice(subcontractors) if random.random() > 0.3 else None
        activity_date = base_date + timedelta(days=random.randint(0, 600))
        
        daily_activity = DailyActivity(
            project_id=project.id,
            subcontractor_id=subcontractor.id if subcontractor else None,
            activity_date=activity_date.strftime("%Y-%m-%d"),
            activity_type=random.choice(["Excavation", "Concrete", "Steel", "Electrical", "Plumbing", "HVAC", "Finishing"]),
            description=f"Daily construction activity - {random.choice(['Foundation work', 'Wall construction', 'Installation', 'Testing', 'Quality check'])}",
            hours_worked=random.randint(4, 12),
            workers_assigned=random.randint(1, 20),
            equipment_used=random.choice(["Excavator", "Crane", "Compressor", "Drill", "Forklift", "None"]),
            materials_used=random.choice(["Concrete", "Steel", "Wood", "Electrical wire", "Pipes", "Paint"]),
            progress_notes=f"Activity {i} progress documented",
            safety_incidents=None if random.random() > 0.1 else "Minor incident reported"
        )
        db.add(daily_activity)
    
    db.commit()
    print(f"✓ Created {count} daily activities")

def seed_documents(db, projects, count=120):
    """Seed documents"""
    print(f"Seeding {count} documents...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        upload_date = base_date + timedelta(days=random.randint(0, 600))
        
        document = Document(
            project_id=project.id,
            document_name=f"Document {i}",
            document_type=random.choice(["Contract", "Drawing", "Specification", "Report", "Manual", "Certificate"]),
            file_path=f"/documents/doc_{i}.pdf",
            uploaded_by=f"User {random.randint(1, 20)}",
            upload_date=upload_date.strftime("%Y-%m-%d"),
            status=random.choice(["Active", "Archived", "Expired"])
        )
        db.add(document)
    
    db.commit()
    print(f"✓ Created {count} documents")

def seed_generated_documents(db, projects, count=1060):
    """Seed generated documents (AI output, reports, etc.)"""
    print(f"Seeding {count} generated documents...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        generated_date = base_date + timedelta(days=random.randint(0, 600))
        
        generated_doc = GeneratedDocument(
            project_id=project.id,
            document_name=f"Generated Report {i}",
            document_type=random.choice(["Daily Report", "Weekly Summary", "Risk Analysis", "Cost Analysis", "Schedule Analysis"]),
            content=f"Auto-generated content for {project.project_name}",
            generated_by=random.choice(["AI Analyzer", "System", "API"]),
            generated_date=generated_date.strftime("%Y-%m-%d"),
            status=random.choice(["Draft", "Published", "Archived"])
        )
        db.add(generated_doc)
    
    db.commit()
    print(f"✓ Created {count} generated documents")

def seed_correspondence(db, projects, count=120):
    """Seed correspondence (emails, letters, etc.)"""
    print(f"Seeding {count} correspondence records...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        correspondence_date = base_date + timedelta(days=random.randint(0, 600))
        
        correspondence = Correspondence(
            project_id=project.id,
            correspondence_type=random.choice(["Email", "Letter", "Memo", "Request", "Notification"]),
            from_party=f"Party {random.randint(1, 20)}",
            to_party=f"Party {random.randint(1, 20)}",
            subject=f"Correspondence Subject {i}",
            content=f"Content of correspondence regarding {project.project_name}",
            correspondence_date=correspondence_date.strftime("%Y-%m-%d"),
            status=random.choice(["Open", "In Review", "Closed"])
        )
        db.add(correspondence)
    
    db.commit()
    print(f"✓ Created {count} correspondence records")

def seed_safety_events(db, projects, subcontractors, count=449):
    """Seed safety events"""
    print(f"Seeding {count} safety events...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        subcontractor = random.choice(subcontractors) if random.random() > 0.3 else None
        event_date = base_date + timedelta(days=random.randint(0, 600))
        
        safety_event = SafetyEvent(
            project_id=project.id,
            subcontractor_id=subcontractor.id if subcontractor else None,
            event_date=event_date.strftime("%Y-%m-%d"),
            event_type=random.choice(["Near Miss", "Minor Injury", "Major Injury", "Hazard Observation", "Close Call"]),
            description=f"Safety event description for incident {i}",
            severity=random.choice(["Low", "Medium", "High", "Critical"]),
            workers_involved=random.randint(1, 5),
            corrective_action=f"Action: {random.choice(['Training', 'Equipment replacement', 'Process change', 'Investigation'])}",
            status=random.choice(["Open", "Investigating", "Resolved", "Closed"])
        )
        db.add(safety_event)
    
    db.commit()
    print(f"✓ Created {count} safety events")

def seed_ncrs(db, projects, suppliers, subcontractors, count=739):
    """Seed NCRs (Non-Conformance Reports)"""
    print(f"Seeding {count} NCRs...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        supplier = random.choice(suppliers) if random.random() > 0.3 else None
        subcontractor = random.choice(subcontractors) if random.random() > 0.3 else None
        ncr_date = base_date + timedelta(days=random.randint(0, 600))
        
        ncr = NCR(
            project_id=project.id,
            supplier_id=supplier.id if supplier else None,
            subcontractor_id=subcontractor.id if subcontractor else None,
            ncr_number=f"NCR-{i:06d}",
            issue_date=ncr_date.strftime("%Y-%m-%d"),
            issue_description=f"Non-conformance: {random.choice(['Quality issue', 'Specification deviation', 'Missing item', 'Defective product'])}",
            severity=random.choice(["Minor", "Major", "Critical"]),
            proposed_resolution=f"Resolution plan for NCR {i}",
            status=random.choice(["Open", "Submitted", "Approved", "Resolved", "Closed"]),
            resolution_date=None if random.random() > 0.6 else (ncr_date + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        )
        db.add(ncr)
    
    db.commit()
    print(f"✓ Created {count} NCRs")

def seed_claims(db, projects, count=120):
    """Seed claims"""
    print(f"Seeding {count} claims...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        claim_date = base_date + timedelta(days=random.randint(0, 600))
        
        claim = Claim(
            project_id=project.id,
            claim_number=f"CLM-{i:05d}",
            claim_date=claim_date.strftime("%Y-%m-%d"),
            claim_type=random.choice(["Extension of Time", "Cost", "Variation", "Delay", "Defect"]),
            claimant=f"Claimant {random.randint(1, 10)}",
            amount=random.uniform(10000, 500000) if random.random() > 0.3 else None,
            description=f"Claim description for claim {i}",
            status=random.choice(["Submitted", "Under Review", "Approved", "Rejected", "Settled"]),
            resolution_date=None if random.random() > 0.5 else (claim_date + timedelta(days=random.randint(10, 120))).strftime("%Y-%m-%d")
        )
        db.add(claim)
    
    db.commit()
    print(f"✓ Created {count} claims")

def seed_change_orders(db, projects, count=120):
    """Seed change orders"""
    print(f"Seeding {count} change orders...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        order_date = base_date + timedelta(days=random.randint(0, 600))
        
        change_order = ChangeOrder(
            project_id=project.id,
            change_order_number=f"CO-{i:06d}",
            issue_date=order_date.strftime("%Y-%m-%d"),
            description=f"Change order {i}: {random.choice(['Scope expansion', 'Specification change', 'Timeline adjustment', 'Material substitution'])}",
            reason=random.choice(["Client request", "Design issue", "Site condition", "Regulatory requirement"]),
            cost_impact=random.uniform(-100000, 200000),
            schedule_impact=random.randint(-30, 60),
            status=random.choice(["Proposed", "Submitted", "Approved", "Implemented", "Closed"]),
            approval_date=None if random.random() > 0.6 else (order_date + timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d")
        )
        db.add(change_order)
    
    db.commit()
    print(f"✓ Created {count} change orders")

def seed_subcontractor_evaluations(db, projects, subcontractors, count=499):
    """Seed subcontractor evaluations"""
    print(f"Seeding {count} subcontractor evaluations...")
    base_date = datetime(2023, 1, 1)
    
    for i in range(1, count + 1):
        project = random.choice(projects)
        subcontractor = random.choice(subcontractors)
        eval_date = base_date + timedelta(days=random.randint(0, 600))
        
        quality = random.randint(1, 10)
        safety = random.randint(1, 10)
        schedule = random.randint(1, 10)
        manpower = random.randint(1, 10)
        overall = (quality + safety + schedule + manpower) / 4
        
        evaluation = SubcontractorEvaluation(
            project_id=project.id,
            subcontractor_id=subcontractor.id,
            evaluation_date=eval_date.strftime("%Y-%m-%d"),
            quality_score=quality,
            safety_score=safety,
            schedule_score=schedule,
            manpower_score=manpower,
            overall_rating=overall,
            comments=f"Evaluation {i}: Performance assessment for {subcontractor.name}"
        )
        db.add(evaluation)
    
    db.commit()
    print(f"✓ Created {count} subcontractor evaluations")

def seed_claim_evidence(db, count=120):
    """Seed claim evidence"""
    print(f"Seeding {count} claim evidence records...")
    base_date = datetime(2023, 1, 1)
    
    # Get claims and other references
    db_session = SessionLocal()
    claims = db_session.query(Claim).all()
    db_session.close()
    
    for i in range(1, count + 1):
        claim = random.choice(claims) if claims else None
        evidence_date = base_date + timedelta(days=random.randint(0, 600))
        
        evidence = ClaimEvidence(
            claim_id=claim.id if claim else None,
            evidence_type=random.choice(["Document", "Photo", "Video", "Email", "Report", "Invoice"]),
            description=f"Evidence {i}: {random.choice(['Supporting document', 'Photographic evidence', 'Communication record'])}",
            file_path=f"/evidence/ev_{i}.pdf" if random.random() > 0.3 else None,
            submitted_date=evidence_date.strftime("%Y-%m-%d"),
            status=random.choice(["Submitted", "Reviewed", "Accepted", "Rejected"])
        )
        db.add(evidence)
    
    db.commit()
    print(f"✓ Created {count} claim evidence records")

def run():
    """Run complete seed"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("SEEDING COMPREHENSIVE DEMO DATASET")
        print("="*60 + "\n")
        
        # Ensure organization exists
        org = db.query(Organization).filter(Organization.slug == "amad-demo").first()
        if not org:
            org = Organization(name="Amad Demo Construction Co.", slug="amad-demo", is_active=True)
            db.add(org)
            db.commit()
            print(f"✓ Created organization")
        
        # Seed in dependency order
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
        print("✓ SEED COMPLETE - All demo data created successfully!")
        print("="*60)
        
        # Print summary
        db2 = SessionLocal()
        print("\nRow count validation:")
        print(f"  projects: {db2.query(Project).count()}")
        print(f"  suppliers: {db2.query(Supplier).count()}")
        print(f"  subcontractors: {db2.query(Subcontractor).count()}")
        print(f"  meetings: {db2.query(Meeting).count()}")
        print(f"  project_decisions: {db2.query(ProjectDecision).count()}")
        print(f"  purchase_requests: {db2.query(PurchaseRequest).count()}")
        print(f"  purchase_orders: {db2.query(PurchaseOrder).count()}")
        print(f"  site_reports: {db2.query(SiteReport).count()}")
        print(f"  daily_activities: {db2.query(DailyActivity).count()}")
        print(f"  documents: {db2.query(Document).count()}")
        print(f"  generated_documents: {db2.query(GeneratedDocument).count()}")
        print(f"  correspondence: {db2.query(Correspondence).count()}")
        print(f"  safety_events: {db2.query(SafetyEvent).count()}")
        print(f"  ncrs: {db2.query(NCR).count()}")
        print(f"  claims: {db2.query(Claim).count()}")
        print(f"  change_orders: {db2.query(ChangeOrder).count()}")
        print(f"  subcontractor_evaluations: {db2.query(SubcontractorEvaluation).count()}")
        print(f"  claim_evidence: {db2.query(ClaimEvidence).count()}")
        db2.close()
        
    finally:
        db.close()


if __name__ == "__main__":
    run()
