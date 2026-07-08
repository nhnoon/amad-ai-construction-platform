#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from app.config import settings

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()

# Add missing columns to organizations table
print("Adding missing columns to organizations table...")
try:
    cur.execute("ALTER TABLE organizations ADD COLUMN slug VARCHAR(100) NOT NULL DEFAULT 'demo'")
    print("✓ Added slug column")
except psycopg2.errors.DuplicateColumn:
    print("  slug column already exists")

try:
    cur.execute("ALTER TABLE organizations ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE")
    print("✓ Added is_active column")
except psycopg2.errors.DuplicateColumn:
    print("  is_active column already exists")

# Create unique index on slug
try:
    cur.execute("CREATE UNIQUE INDEX ix_organizations_slug ON organizations(slug)")
    print("✓ Created slug index")
except psycopg2.errors.DuplicateObject:
    print("  slug index already exists")

conn.commit()
cur.close()
conn.close()
print("✓ Organizations table updated successfully")
