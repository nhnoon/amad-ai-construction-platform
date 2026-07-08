#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from app.config import settings

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()

# Drop dependent tables first
print("Dropping and recreating subcontractor-related tables...")
try:
    cur.execute("DROP TABLE IF EXISTS subcontractor_evaluations CASCADE")
    print("✓ Dropped subcontractor_evaluations table")
except Exception as e:
    print(f"  Warning: {e}")

try:
    cur.execute("DROP TABLE IF EXISTS subcontractors CASCADE")
    print("✓ Dropped subcontractors table")
except Exception as e:
    print(f"  Warning: {e}")

# Recreate with correct structure
cur.execute("""
CREATE TABLE subcontractors (
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
)
""")
print("✓ Created subcontractors table")

cur.execute("""
CREATE TABLE subcontractor_evaluations (
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
    linked_safety_event_id INTEGER,
    linked_ncr_id INTEGER,
    linked_daily_activity_id INTEGER
)
""")
print("✓ Created subcontractor_evaluations table")

conn.commit()
cur.close()
conn.close()
print("✓ Tables recreated successfully")
