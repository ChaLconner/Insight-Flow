"""Fix alembic version and add starter plan using psycopg2

This script:
1. Fixes the orphaned alembic_version to match existing migration files
2. Adds 'starter' value to subscriptionplan enum

Run this manually when database connectivity is slow/timeout issues.
"""

import os
import sys

# Add backend path
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")


def fix_database():
    import psycopg2

    from config import get_settings

    settings = get_settings()
    db_url = settings.database.url

    print("Connecting to database...")
    print(f"URL prefix: {db_url[:50]}...")

    conn = psycopg2.connect(db_url)
    conn.autocommit = True  # Required for ALTER TYPE
    cur = conn.cursor()

    try:
        # Step 1: Check current alembic version
        cur.execute("SELECT version_num FROM alembic_version")
        current = cur.fetchone()
        current_version = current[0] if current else None
        print(f"Current alembic version: {current_version}")

        # Step 2: Fix alembic version if it's orphaned
        valid_revisions = [
            "add_payment_tables_001",
            "add_starter_plan_001",
            "add_github_id_001",
            "58e012fdb79c",
        ]
        if current_version and current_version not in valid_revisions:
            print(f"Fixing orphaned revision '{current_version}' -> 'add_payment_tables_001'")
            cur.execute("UPDATE alembic_version SET version_num = 'add_payment_tables_001'")
            print("Fixed!")

        # Step 3: Check if 'starter' exists in enum
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = 'starter'
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subscriptionplan')
            )
        """)
        starter_exists = cur.fetchone()[0]

        if not starter_exists:
            print("Adding 'starter' to subscriptionplan enum...")
            cur.execute(
                "ALTER TYPE subscriptionplan ADD VALUE IF NOT EXISTS 'starter' AFTER 'free'"
            )
            print("Added 'starter' value to enum!")
        else:
            print("'starter' already exists in enum")

        # Step 4: Update alembic version to latest
        cur.execute("UPDATE alembic_version SET version_num = 'add_starter_plan_001'")
        print("Updated alembic version to 'add_starter_plan_001'")

        # Verify
        cur.execute(
            "SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'subscriptionplan') ORDER BY enumsortorder"
        )
        enum_values = [row[0] for row in cur.fetchall()]
        print(f"Current enum values: {enum_values}")

    finally:
        cur.close()
        conn.close()

    print("Done!")


if __name__ == "__main__":
    fix_database()
