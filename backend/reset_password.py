import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from utils.auth import get_password_hash

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

email = "chaluntonvipusanapas@gmail.com"
new_password = "password123"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Generate new password hash
        new_hash = get_password_hash(new_password)
        
        # Update password in database
        result = conn.execute(
            text("UPDATE users SET hashed_password = :hash WHERE email = :email"),
            {"hash": new_hash, "email": email}
        )
        conn.commit()
        
        print(f"Password reset successful for {email}")
        print(f"New password: {new_password}")
        
except Exception as e:
    print(f"Error: {e}")