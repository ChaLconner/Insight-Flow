import os
import sys

# Add current directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, engine


def create_tables():
    print("Creating user_settings table...")
    Base.metadata.create_all(bind=engine)
    print("Table created successfully.")


if __name__ == "__main__":
    create_tables()
