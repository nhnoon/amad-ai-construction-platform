#!/usr/bin/env python
import os
import sys
from app.database import SessionLocal
from sqlalchemy import text

# List of tables to check
tables = [
    'organizations',
    'user_accounts',
    'projects',
    'suppliers',
    'subcontractors',
    'meetings',
    'project_decisions',
    'purchase_requests',
    'purchase_orders',
    'site_reports',
    'daily_activities',
    'documents',
    'generated_documents',
    'correspondence',
    'safety_events',
    'ncrs',
    'claims',
    'change_orders',
    'subcontractor_evaluations',
    'claim_evidence'
]

db = SessionLocal()
try:
    print("Current PostgreSQL Database Counts:")
    print("=" * 50)
    
    for table in tables:
        try:
            result = db.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
            count = result.scalar()
            print(f"{table:.<40} {count:>6}")
        except Exception as e:
            print(f"{table:.<40} ERROR: {str(e)[:30]}")
    
    print("=" * 50)
finally:
    db.close()
