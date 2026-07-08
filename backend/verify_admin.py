import sys
sys.path.insert(0, '.')
from app.database import SessionLocal
from app.models.auth import UserAccount
from app.core.security import verify_password

db = SessionLocal()
user = db.query(UserAccount).filter(UserAccount.email=='admin@construction.ai').first()

if user:
    print(f"Found user: {user.email}")
    print(f"Is active: {user.is_active}")
    print(f"Role: {user.role}")
    print(f"Full name: {user.full_name}")
    
    # Test password verification
    is_valid = verify_password('Admin123!', user.hashed_password)
    print(f"Password verify Admin123!: {is_valid}")
    
    if is_valid:
        print("✓ Login should work!")
    else:
        print("✗ Password mismatch!")
else:
    print("User not found!")

db.close()
