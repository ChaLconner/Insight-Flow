import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models.user import User
from utils.auth import create_access_token
from datetime import timedelta

db = SessionLocal()
user = db.query(User).filter(User.email == 'admin@example.com').first()
if user:
    print('User found: {}, ID: {}'.format(user.email, user.id))
    # Create token with longer expiry
    token = create_access_token(data={'sub': str(user.id)}, expires_delta=timedelta(hours=24))
    print('New token: {}'.format(token))
else:
    print('User not found')
db.close()