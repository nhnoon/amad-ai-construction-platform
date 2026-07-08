#!/usr/bin/env python
"""
Examine actual data in database to determine which seed script was used.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.projects import Project
from app.models.procurement import Supplier
from app.models.subcontractors import Subcontractor

db = SessionLocal()

print("\n" + "="*70)
print("ANALYZING DATABASE CONTENT")
print("="*70)

# Check projects
projects = db.query(Project).limit(3).all()
print("\nSample PROJECTS:")
for p in projects:
    print(f"  ID: {p.id:3} | Name: {p.project_name:30} | Code: {p.project_code}")

# Check suppliers
suppliers = db.query(Supplier).limit(3).all()
print("\nSample SUPPLIERS:")
for s in suppliers:
    print(f"  ID: {s.id:3} | Name: {s.supplier_name:30} | Category: {s.category}")

# Check subcontractors
subcontractors = db.query(Subcontractor).limit(3).all()
print("\nSample SUBCONTRACTORS:")
for s in subcontractors:
    print(f"  ID: {s.id:3} | Name: {s.name:30} | Trade: {s.trade}")

# Count totals
projects_count = db.query(Project).count()
suppliers_count = db.query(Supplier).count()
subcontractors_count = db.query(Subcontractor).count()

print("\n" + "="*70)
print("TOTAL COUNTS:")
print(f"  Projects: {projects_count}")
print(f"  Suppliers: {suppliers_count}")
print(f"  Subcontractors: {subcontractors_count}")
print("="*70)

# Analysis
print("\nANALYSIS:")
if projects and "Construction Project" in projects[0].project_name:
    print("✓ Data MATCHES seed script pattern: 'Construction Project {i}'")
    print("✓ This is GENERATED placeholder data")
    print("✗ NOT from original SQL dump")
elif projects:
    print(f"✓ Data has REALISTIC names: '{projects[0].project_name}'")
    print("✓ This appears to be from original SQL dump")

print("\n" + "="*70 + "\n")

db.close()
