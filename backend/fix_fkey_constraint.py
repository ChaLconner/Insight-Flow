
import sys
import os
import sqlalchemy
from sqlalchemy import text

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine

def fix_constraint():
    print("Fixing Foreign Key constraint on task_history table...")
    with engine.connect() as connection:
        try:
            # Check if constraint exists (postgres specific)
            result = connection.execute(text("SELECT 1 FROM pg_constraint WHERE conname = 'task_history_task_id_fkey'"))
            if result.scalar():
                print("Dropping existing constraint...")
                connection.execute(text("ALTER TABLE task_history DROP CONSTRAINT task_history_task_id_fkey"))
                
            print("Adding new constraint with ON DELETE SET NULL...")
            connection.execute(text("ALTER TABLE task_history ADD CONSTRAINT task_history_task_id_fkey FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL"))
            
            connection.commit()
            print("Constraint updated successfully!")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fix_constraint()
