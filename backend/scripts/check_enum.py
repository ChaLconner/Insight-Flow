from database import engine
from sqlalchemy import text

# ตรวจสอบค่า enum ใน database
with engine.connect() as conn:
    result = conn.execute(text("SELECT unnest(enum_range(NULL::task_status))"))
    enum_values = [row[0] for row in result]
    print('Current enum values in database:', enum_values)