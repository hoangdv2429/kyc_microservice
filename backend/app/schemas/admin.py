from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID

class KYCReview(BaseModel):
    decision: str  # "passed" or "rejected"
    reviewer_id: UUID
    note: Optional[str] = None

class KYCReviewRequest(BaseModel):
    status: str  # "passed" or "rejected"
    kyc_tier: int
    note: Optional[str] = None
    reviewer_id: UUID

class PendingKYC(BaseModel):
    ticket_id: UUID
    user_id: UUID
    status: str
    submitted_at: datetime
    full_name: str
    email: Optional[str] = None
    risk_score: Optional[float] = None
    # Document URLs for admin review
    doc_front: Optional[str] = None
    doc_back: Optional[str] = None
    selfie: Optional[str] = None
    # Additional verification metrics
    face_score: Optional[float] = None
    liveness_score: Optional[float] = None
    
    class Config:
        from_attributes = True

class KYCJobAdmin(BaseModel):
    ticket_id: UUID
    user_id: UUID
    status: str
    kyc_tier: int
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[UUID] = None
    note: Optional[str] = None
    auto_approved: bool
    risk_score: Optional[float] = None
    face_score: Optional[float] = None
    liveness_score: Optional[float] = None
    # Personal info (decrypted for admin view)
    full_name: str
    dob: str
    address: str
    email: Optional[str] = None
    phone: Optional[str] = None
    # Technical details
    ocr_json: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class AdminDashboard(BaseModel):
    total_submissions: int
    pending_reviews: int
    passed_kyc: int
    rejected_kyc: int
    tier_0_count: int
    tier_1_count: int
    tier_2_count: int
    recent_submissions_7d: int
    avg_processing_time_hours: float
    approval_rate: float

class KYCStats(BaseModel):
    period_days: int
    total_submissions: int
    auto_approved: int
    manual_reviewed: int
    pending: int
    avg_face_score: float
    avg_liveness_score: float
    avg_risk_score: float
    processing_time_avg: float

class AuditLogResponse(BaseModel):
    id: int
    action: str
    user_id: Optional[UUID] = None
    kyc_job_id: Optional[UUID] = None
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True 