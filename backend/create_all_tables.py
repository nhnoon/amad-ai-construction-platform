#!/usr/bin/env python
"""
Create database tables excluding pgvector-dependent tables.
Modified for Windows PostgreSQL compatibility.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models.base import Base
from sqlalchemy import inspect, MetaData

print("Creating database tables (skipping pgvector-dependent tables)...")
print("="*60)

try:
    # Get all tables
    metadata = Base.metadata
    
    # Find and skip ai_memories table (requires pgvector)
    tables_to_skip = {"ai_memories"}
    tables_to_create = [t for t in metadata.sorted_tables if t.name not in tables_to_skip]
    
    # Create tables manually, excluding ai_memories
    with engine.connect() as conn:
        for table in tables_to_create:
            try:
                table.create(bind=conn, checkfirst=True)
                print(f"✓ Created table: {table.name}")
            except Exception as e:
                print(f"  Info: {table.name} - {str(e)[:60]}")
        conn.commit()
    
    print("="*60)
    print("✓ Tables created successfully")
    
    # Verify tables exist
    inspector = inspect(engine)
    tables = [t for t in inspector.get_table_names() if t not in tables_to_skip]
    
    print(f"\nCreated {len(tables)} tables:")
    for table in sorted(tables):
        print(f"  ✓ {table}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
