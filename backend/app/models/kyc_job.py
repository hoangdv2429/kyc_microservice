from sqlalchemy import Column, String, DateTime, Float, ForeignKey, JSON, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.models.base import Base

class KYCJob(Base):
    ticket_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    submitted_at = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)  # pending/processing/passed/rejected/manual_review
    kyc_tier = Column(Integer, default=0)  # 0=view, 1=basic, 2=full
    doc_front = Column(String)  # S3 key
    doc_back = Column(String)  # S3 key
    selfie = Column(String)  # S3 key
    ocr_json = Column(JSONB)
    face_score = Column(Float)
    liveness_score = Column(Float)
    sanctions_hit = Column(JSONB)
    reviewer_id = Column(UUID(as_uuid=True), ForeignKey("user.id"))
    reviewed_at = Column(DateTime)
    note = Column(String)
    auto_approved = Column(Boolean, default=False)
    risk_score = Column(Float)
    # New personal info fields
    full_name = Column(String, nullable=False)
    dob = Column(String, nullable=False)
    address = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    # Compliance fields
    data_retention_until = Column(DateTime)
    deletion_requested_at = Column(DateTime)
    encrypted_data = Column(JSONB)  # For AES-256 encrypted sensitive data 