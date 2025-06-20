from typing import Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, validator
from uuid import UUID
from datetime import datetime

class KYCSubmit(BaseModel):
    user_id: UUID
    full_name: str
    dob: str
    address: str
    email: Optional[str]
    phone: Optional[str]
    doc_front_url: HttpUrl
    doc_back_url: HttpUrl
    selfie_url: HttpUrl
    requested_tier: Optional[int] = 2  # Default to full KYC
    
    @validator('requested_tier')
    def validate_tier(cls, v):
        if v not in [1, 2]:
            raise ValueError('Requested tier must be 1 or 2')
        return v

class KYCStatus(BaseModel):
    ticket_id: UUID
    status: str
    kyc_tier: int
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    note: Optional[str] = None
    risk_score: Optional[float] = None
    face_score: Optional[float] = None
    liveness_score: Optional[float] = None
    auto_approved: bool = False
    # Technical details (optional)
    ocr_json: Optional[Dict[str, Any]] = None
    sanctions_hit: Optional[Dict[str, Any]] = None

class KYCTierInfo(BaseModel):
    tier: int
    name: str
    description: str
    features: list[str]
    limits: Dict[str, Any]

class KYCVerificationResult(BaseModel):
    verified: bool
    tier_achieved: int
    confidence_score: float
    checks_passed: Dict[str, bool]
    details: Dict[str, Any]

class SmartContractStatus(BaseModel):
    user_address: str
    kyc_tier: int
    approved: bool
    withdrawal_eligible: bool
    last_updated: datetime 