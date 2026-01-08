import uuid

from sqlalchemy import JSON, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base


class SecurityLog(Base):
    __tablename__ = "security_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    severity = Column(String(20), nullable=False, default="info")

    # Context
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    request_path = Column(String(255), nullable=True)
    request_method = Column(String(10), nullable=True)

    # Detailed info
    details = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<SecurityLog {self.event_type} at {self.timestamp}>"
