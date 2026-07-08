import psycopg2

conn = psycopg2.connect('postgresql://postgres:Admin123!@localhost:5432/amad_construction_ai')
cur = conn.cursor()

# Drop existing tables if they exist
cur.execute("DROP TABLE IF EXISTS project_memberships CASCADE")
cur.execute("DROP TABLE IF EXISTS user_accounts CASCADE")
cur.execute("DROP TABLE IF EXISTS organizations CASCADE")

# Create minimal schema for auth
cur.execute('''
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
)
''')

cur.execute('''
CREATE TABLE user_accounts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT true,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_login TIMESTAMP WITH TIME ZONE
)
''')

cur.execute('''
CREATE TABLE project_memberships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user_accounts(id),
    project_id INTEGER,
    role VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
)
''')

conn.commit()
print('Schema recreated successfully')
cur.close()
conn.close()
