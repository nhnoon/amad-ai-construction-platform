#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from app.config import settings

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()

# Truncate all tables in correct order (respecting foreign keys)
tables_to_truncate = [
    "claim_evidence",
    "subcontractor_evaluations",
    "change_orders",
    "claims",
    "ncrs",
    "safety_events",
    "correspondence",
    "generated_documents",
    "documents",
    "daily_activities",
    "site_reports",
    "purchase_orders",
    "purchase_requests",
    "project_decisions",
    "meetings",
    "subcontractors",
    "suppliers",
    "projects"
]

print("Truncating all data tables...")
for table in tables_to_truncate:
    try:
        cur.execute(f"TRUNCATE TABLE {table} CASCADE")
        print(f"✓ Truncated {table}")
    except Exception as e:
        print(f"  Error truncating {table}: {e}")

# Reset sequences
print("\nResetting sequences...")
for table in tables_to_truncate:
    try:
        cur.execute(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1")
        print(f"✓ Reset sequence {table}_id_seq")
    except Exception:
        pass

conn.commit()
cur.close()
conn.close()
print("✓ All data tables cleared successfully")
