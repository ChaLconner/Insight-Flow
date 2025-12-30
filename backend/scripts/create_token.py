import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import timedelta

from database import SessionLocal
from models.user import User
from utils.auth import create_access_token

db = SessionLocal()
user = db.query(User).filter(User.email == "admin@example.com").first()
if user:
    print(f"User found: {user.email}, ID: {user.id}")
    # Create token with longer expiry
    token = create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(hours=24))
    print(f"New token: {token}")
else:
    print("User not found")
db.close()
