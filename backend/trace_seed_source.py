#!/usr/bin/env python
"""
Trace which seed script was used to populate the database.
Check execution timestamps and file dates.
"""
import os
from datetime import datetime

backend_dir = os.path.dirname(os.path.abspath(__file__))

scripts = [
    "scripts/seed_demo_data.py",
    "scripts/seed_demo_data_corrected.py",
    "scripts/migrate_sqlite.py",
]

print("\n" + "="*70)
print("SEED SCRIPT FILE INFORMATION")
print("="*70 + "\n")

for script in scripts:
    full_path = os.path.join(backend_dir, script)
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        mtime = os.path.getmtime(full_path)
        mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"{script}")
        print(f"  Size: {size} bytes")
        print(f"  Modified: {mod_time}")
        print()
    else:
        print(f"{script}: FILE NOT FOUND")
        print()

print("="*70)
print("KEY OBSERVATIONS:")
print("="*70)

# Check if SQL dump exists
dump_path = os.path.abspath(os.path.join(backend_dir, "../../attached_assets/sql_dataset/construction_ai_dataset_full_dump.sql"))
print(f"\nOriginal SQL Dump: {dump_path}")
print(f"  EXISTS: {os.path.exists(dump_path)}")

if not os.path.exists(dump_path):
    print("\n⚠️  SQL DUMP IS MISSING - This explains why generated seed data was used!")

print("\n" + "="*70 + "\n")
