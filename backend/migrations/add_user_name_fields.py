"""
Migration script to add first_name and last_name fields to users table.
"""

import os
import sys

from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import database_url as DATABASE_URL


def add_name_fields():
    """Add first_name and last_name columns to users table."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as connection:
        # Check if columns already exist
        result = connection.execute(
            text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND column_name IN ('first_name', 'last_name')
        """)
        ).fetchall()

        existing_columns = [row[0] for row in result]

        # Add first_name column if it doesn't exist
        if "first_name" not in existing_columns:
            connection.execute(
                text("""
                ALTER TABLE users
                ADD COLUMN first_name VARCHAR(255)
            """)
            )
            print("Added first_name column to users table")
        else:
            print("first_name column already exists")

        # Add last_name column if it doesn't exist
        if "last_name" not in existing_columns:
            connection.execute(
                text("""
                ALTER TABLE users
                ADD COLUMN last_name VARCHAR(255)
            """)
            )
            print("Added last_name column to users table")
        else:
            print("last_name column already exists")

        # Migrate existing name data to first_name and last_name
        connection.execute(
            text("""
            UPDATE users
            SET
                first_name = CASE
                    WHEN POSITION(' ' IN name) > 0
                    THEN SUBSTRING(name, 1, POSITION(' ' IN name) - 1)
                    ELSE name
                END,
                last_name = CASE
                    WHEN POSITION(' ' IN name) > 0
                    THEN SUBSTRING(name, POSITION(' ' IN name) + 1)
                    ELSE ''
                END
            WHERE name IS NOT NULL
            AND (first_name IS NULL OR last_name IS NULL)
        """)
        )
        print("Migrated existing name data to first_name and last_name")

        # Make name column nullable to support first_name/last_name
        connection.execute(
            text("""
            ALTER TABLE users
            ALTER COLUMN name DROP NOT NULL
        """)
        )
        print("Made name column nullable")

        connection.commit()


if __name__ == "__main__":
    add_name_fields()
    print("Migration completed successfully!")
