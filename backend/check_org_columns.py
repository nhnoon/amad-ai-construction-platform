#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from app.config import settings

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'organizations' ORDER BY ordinal_position")
print('Columns in organizations table:')
for row in cur.fetchall():
    print(f'  {row[0]}')
cur.close()
conn.close()
