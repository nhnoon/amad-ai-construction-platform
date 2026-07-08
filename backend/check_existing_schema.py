#!/usr/bin/env python
import os
import sys
from app.database import SessionLocal
from sqlalchemy import text, inspect

db = SessionLocal()
try:
    inspector = inspect(db.get_bind())
    tables = inspector.get_table_names()
    
    print("Existing tables in database:")
    print("="*50)
    for table in sorted(tables):
        result = db.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
        count = result.scalar()
        print(f"{table:.<40} {count:>6}")
    
    print("="*50)
    print(f"Total tables: {len(tables)}")
finally:
    db.close()
