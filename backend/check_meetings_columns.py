#!/usr/bin/env python
import sys, os
sys.path.insert(0, os.getcwd())
from app.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
columns = inspector.get_columns('meetings')
print('Columns in meetings table:')
for col in columns:
    print(f'  - {col["name"]}: {col["type"]}')
