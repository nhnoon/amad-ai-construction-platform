#!/usr/bin/env python
"""
Create complete database schema without pgvector (Windows compatibility).
Run once before seeding demo data.

Usage:
    cd backend && python create_schema_windows.py
"""
import os
import sys
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# All CREATE TABLE statements - complete schema without pgvector
CREATE_TABLE_SQL = """
-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    project_code VARCHAR(50) NOT NULL UNIQUE,
    project_name VARCHAR(255) NOT NULL,
    project_type VARCHAR(100) NOT NULL,
    client_name VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    start_date VARCHAR(50) NOT NULL,
    planned_finish VARCHAR(50) NOT NULL,
    actual_finish VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    budget FLOAT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_projects_status ON projects(status);

-- Suppliers
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    supplier_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL
);

-- Subcontractors
CREATE TABLE IF NOT EXISTS subcontractors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    trade VARCHAR(100) NOT NULL,
    contact_person VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,
    classification VARCHAR(50) NOT NULL,
    city VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at VARCHAR(50) NOT NULL
);

-- Meetings
CREATE TABLE IF NOT EXISTS meetings (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    meeting_title VARCHAR(255) NOT NULL,
    meeting_date VARCHAR(50) NOT NULL,
    meeting_type VARCHAR(100) NOT NULL,
    attendees TEXT NOT NULL,
    summary TEXT,
    action_items TEXT
);

-- Project Decisions
CREATE TABLE IF NOT EXISTS project_decisions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    meeting_id INTEGER REFERENCES meetings(id),
    decision TEXT NOT NULL,
    decision_date VARCHAR(50) NOT NULL,
    owner VARCHAR(255),
    status VARCHAR(50) NOT NULL
);

-- Purchase Requests
CREATE TABLE IF NOT EXISTS purchase_requests (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    request_no VARCHAR(50) NOT NULL,
    material_category VARCHAR(100),
    specification TEXT,
    required_delivery_date VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    rework_reason TEXT,
    created_at VARCHAR(50) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_purchase_requests_project_id ON purchase_requests(project_id);
CREATE INDEX IF NOT EXISTS ix_purchase_requests_status ON purchase_requests(status);

-- Purchase Orders
CREATE TABLE IF NOT EXISTS purchase_orders (
    id SERIAL PRIMARY KEY,
    pr_id INTEGER NOT NULL REFERENCES purchase_requests(id),
    project_id INTEGER NOT NULL REFERENCES projects(id),
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    po_number VARCHAR(50) NOT NULL,
    issue_date VARCHAR(50) NOT NULL,
    promised_delivery VARCHAR(50) NOT NULL,
    actual_delivery VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    delay_days INTEGER NOT NULL DEFAULT 0,
    delay_root_cause TEXT
);
CREATE INDEX IF NOT EXISTS ix_purchase_orders_supplier_id ON purchase_orders(supplier_id);
CREATE INDEX IF NOT EXISTS ix_purchase_orders_is_late ON purchase_orders(is_late);

-- Site Reports
CREATE TABLE IF NOT EXISTS site_reports (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    report_date VARCHAR(50) NOT NULL,
    report_type VARCHAR(100) NOT NULL,
    site_manager VARCHAR(255),
    weather VARCHAR(100),
    workers_on_site INTEGER,
    equipment_status VARCHAR(100),
    progress_percentage INTEGER,
    summary TEXT,
    issues TEXT
);

-- Daily Activities
CREATE TABLE IF NOT EXISTS daily_activities (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    subcontractor_id INTEGER REFERENCES subcontractors(id),
    activity_date VARCHAR(50) NOT NULL,
    activity_type VARCHAR(100) NOT NULL,
    description TEXT,
    hours_worked INTEGER,
    workers_assigned INTEGER,
    equipment_used VARCHAR(255),
    materials_used VARCHAR(255),
    progress_notes TEXT,
    safety_incidents TEXT
);

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    file_path VARCHAR(500),
    uploaded_by VARCHAR(255),
    upload_date VARCHAR(50),
    status VARCHAR(50)
);

-- Generated Documents
CREATE TABLE IF NOT EXISTS generated_documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    content TEXT,
    generated_by VARCHAR(255),
    generated_date VARCHAR(50),
    status VARCHAR(50)
);

-- Correspondence
CREATE TABLE IF NOT EXISTS correspondence (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    correspondence_type VARCHAR(100) NOT NULL,
    from_party VARCHAR(255),
    to_party VARCHAR(255),
    subject VARCHAR(500),
    content TEXT,
    correspondence_date VARCHAR(50),
    status VARCHAR(50)
);

-- Safety Events
CREATE TABLE IF NOT EXISTS safety_events (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    subcontractor_id INTEGER REFERENCES subcontractors(id),
    event_date VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    description TEXT,
    severity VARCHAR(50),
    workers_involved INTEGER,
    corrective_action TEXT,
    status VARCHAR(50)
);

-- NCRs (Non-Conformance Reports)
CREATE TABLE IF NOT EXISTS ncrs (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    subcontractor_id INTEGER REFERENCES subcontractors(id),
    ncr_number VARCHAR(50) NOT NULL,
    issue_date VARCHAR(50) NOT NULL,
    issue_description TEXT NOT NULL,
    severity VARCHAR(50),
    proposed_resolution TEXT,
    status VARCHAR(50),
    resolution_date VARCHAR(50)
);

-- Claims
CREATE TABLE IF NOT EXISTS claims (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    claim_number VARCHAR(50) NOT NULL,
    claim_date VARCHAR(50) NOT NULL,
    claim_type VARCHAR(100),
    claimant VARCHAR(255),
    amount FLOAT,
    description TEXT,
    status VARCHAR(50),
    resolution_date VARCHAR(50)
);

-- Change Orders
CREATE TABLE IF NOT EXISTS change_orders (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    change_order_number VARCHAR(50) NOT NULL,
    issue_date VARCHAR(50) NOT NULL,
    description TEXT,
    reason VARCHAR(255),
    cost_impact FLOAT,
    schedule_impact INTEGER,
    status VARCHAR(50),
    approval_date VARCHAR(50)
);

-- Subcontractor Evaluations
CREATE TABLE IF NOT EXISTS subcontractor_evaluations (
    id SERIAL PRIMARY KEY,
    subcontractor_id INTEGER NOT NULL REFERENCES subcontractors(id),
    project_id INTEGER NOT NULL REFERENCES projects(id),
    evaluation_date VARCHAR(50) NOT NULL,
    quality_score INTEGER NOT NULL,
    safety_score INTEGER NOT NULL,
    schedule_score INTEGER NOT NULL,
    manpower_score INTEGER NOT NULL,
    overall_rating FLOAT NOT NULL,
    comments TEXT NOT NULL,
    linked_safety_event_id INTEGER REFERENCES safety_events(id),
    linked_ncr_id INTEGER REFERENCES ncrs(id),
    linked_daily_activity_id INTEGER REFERENCES daily_activities(id)
);

-- Claim Evidence
CREATE TABLE IF NOT EXISTS claim_evidence (
    id SERIAL PRIMARY KEY,
    claim_id INTEGER REFERENCES claims(id),
    evidence_type VARCHAR(100),
    description TEXT,
    file_path VARCHAR(500),
    submitted_date VARCHAR(50),
    status VARCHAR(50)
);

-- Project Phases
CREATE TABLE IF NOT EXISTS project_phases (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    name VARCHAR(255) NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 1,
    start_date VARCHAR(50),
    end_date VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'planned'
);

-- Project Milestones
CREATE TABLE IF NOT EXISTS project_milestones (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    phase_id INTEGER REFERENCES project_phases(id),
    name VARCHAR(255) NOT NULL,
    planned_date VARCHAR(50) NOT NULL,
    actual_date VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
);

-- Project Risks
CREATE TABLE IF NOT EXISTS project_risks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    probability VARCHAR(20) NOT NULL DEFAULT 'medium',
    impact VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    owner VARCHAR(255),
    mitigation TEXT,
    created_at VARCHAR(50)
);

-- Project Issues
CREATE TABLE IF NOT EXISTS project_issues (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    owner VARCHAR(255),
    resolution TEXT,
    created_at VARCHAR(50),
    resolved_at VARCHAR(50)
);
"""

def run():
    """Create all tables"""
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        
        cursor = conn.cursor()
        
        # Execute all CREATE TABLE statements
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
        
        print("✓ Schema created successfully (Windows compatible - no pgvector)")
        print("Ready to seed demo data")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
