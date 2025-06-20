from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.base import Base

class AuditLog(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    kyc_job_id = Column(UUID(as_uuid=True), ForeignKey("kycjob.ticket_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    details = Column(JSON) 