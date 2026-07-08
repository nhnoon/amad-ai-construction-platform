#!/usr/bin/env python
"""
Drop all existing tables and recreate from SQLAlchemy models.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from app.models.base import Base
from sqlalchemy import inspect

print("Dropping all existing tables...")
print("="*60)

try:
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    print("✓ All tables dropped")
    
    # Recreate tables
    print("\nCreating all tables from SQLAlchemy models...")
    
    # Get all tables except ai_memories (requires pgvector)
    tables_to_skip = {"ai_memories"}
    tables_to_create = [t for t in Base.metadata.sorted_tables if t.name not in tables_to_skip]
    
    with engine.connect() as conn:
        for table in tables_to_create:
            try:
                table.create(bind=conn, checkfirst=True)
                print(f"✓ Created table: {table.name}")
            except Exception as e:
                if "already exists" not in str(e):
                    print(f"  Warning: {table.name} - {str(e)[:60]}")
        conn.commit()
    
    print("="*60)
    print("✓ Database recreated successfully")
    
    # Verify
    inspector = inspect(engine)
    tables = [t for t in inspector.get_table_names() if t not in tables_to_skip]
    print(f"\nCreated {len(tables)} tables")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
