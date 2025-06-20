from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.kyc_job import KYCJob
from app.models.user import User
from app.schemas.kyc import (
    KYCSubmit, KYCStatus, KYCTierInfo, 
    KYCVerificationResult, SmartContractStatus
)
from app.workers.tasks import process_kyc
from app.models.audit_log import AuditLog
from app.services.contract_service import SmartContractService

router = APIRouter()
contract_service = SmartContractService()

@router.post("/submit", response_model=dict[str, UUID])
async def submit_kyc(
    *,
    db: Session = Depends(get_db),
    kyc_data: KYCSubmit,
) -> Any:
    """
    Submit a new KYC verification request with tier support.
    """
    # TODO: remove this check in production
    # Create user if it doesn't exist
    user = db.query(User).filter(User.id == kyc_data.user_id).first()
    if not user:
        user = User(
            id=kyc_data.user_id,
            email=kyc_data.email,
            phone=kyc_data.phone
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Check if user already has pending KYC
    existing_kyc = db.query(KYCJob).filter(
        KYCJob.user_id == kyc_data.user_id,
        KYCJob.status.in_(["pending", "processing", "manual_review"])
    ).first()
    
    if existing_kyc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has pending KYC verification",
        )

    # Create new KYC job
    kyc_job = KYCJob(
        user_id=kyc_data.user_id,
        submitted_at=datetime.utcnow(),
        status="pending",
        kyc_tier=0,  # Will be determined after processing
        doc_front=str(kyc_data.doc_front_url),
        doc_back=str(kyc_data.doc_back_url),
        selfie=str(kyc_data.selfie_url),
        full_name=kyc_data.full_name,
        dob=kyc_data.dob,
        address=kyc_data.address,
        email=kyc_data.email,
        phone=kyc_data.phone,
    )
    db.add(kyc_job)
    db.commit()
    db.refresh(kyc_job)

    # Trigger async KYC processing
    process_kyc.delay(str(kyc_job.ticket_id))

    # Log for audit
    audit_log = AuditLog(
        action="submit_kyc",
        user_id=kyc_data.user_id,
        kyc_job_id=kyc_job.ticket_id,
        timestamp=datetime.utcnow(),
        details={
            "info": "KYC submission created",
            "requested_tier": kyc_data.requested_tier
        }
    )
    db.add(audit_log)
    db.commit()

    return {"ticket_id": kyc_job.ticket_id}

@router.get("/status/{ticket_id}", response_model=KYCStatus)
async def get_kyc_status(
    ticket_id: UUID,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get the status of a KYC verification request.
    """
    kyc_job = db.query(KYCJob).filter(KYCJob.ticket_id == ticket_id).first()
    if not kyc_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC job not found",
        )
    
    return KYCStatus(
        ticket_id=kyc_job.ticket_id,
        status=kyc_job.status,
        kyc_tier=kyc_job.kyc_tier,
        submitted_at=kyc_job.submitted_at,
        reviewed_at=kyc_job.reviewed_at,
        note=kyc_job.note,
        risk_score=kyc_job.risk_score,
        face_score=kyc_job.face_score,
        liveness_score=kyc_job.liveness_score,
        auto_approved=kyc_job.auto_approved,
        ocr_json=kyc_job.ocr_json,
        sanctions_hit=kyc_job.sanctions_hit,
    )

@router.get("/tiers", response_model=List[KYCTierInfo])
async def get_kyc_tiers() -> Any:
    """
    Get information about available KYC tiers.
    """
    return [
        KYCTierInfo(
            tier=0,
            name="View Only",
            description="Basic account access without withdrawal privileges",
            features=["View balance", "View transactions", "Basic platform access"],
            limits={"withdrawal": 0, "daily_limit": 0}
        ),
        KYCTierInfo(
            tier=1,
            name="Basic KYC",
            description="Limited KYC with basic verification",
            features=["Limited withdrawals", "Basic trading", "Standard support"],
            limits={"withdrawal": 1000, "daily_limit": 1000}
        ),
        KYCTierInfo(
            tier=2,
            name="Full KYC",
            description="Complete KYC verification with full access",
            features=["Unlimited withdrawals", "Full trading access", "Priority support", "Advanced features"],
            limits={"withdrawal": -1, "daily_limit": -1}  # -1 means unlimited
        )
    ]

@router.get("/user/{user_id}/status", response_model=KYCStatus)
async def get_user_kyc_status(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get the latest KYC status for a specific user.
    """
    kyc_job = db.query(KYCJob).filter(
        KYCJob.user_id == user_id
    ).order_by(KYCJob.submitted_at.desc()).first()
    
    if not kyc_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No KYC submission found for this user",
        )
    
    return KYCStatus(
        ticket_id=kyc_job.ticket_id,
        status=kyc_job.status,
        kyc_tier=kyc_job.kyc_tier,
        submitted_at=kyc_job.submitted_at,
        reviewed_at=kyc_job.reviewed_at,
        note=kyc_job.note,
        risk_score=kyc_job.risk_score,
        face_score=kyc_job.face_score,
        liveness_score=kyc_job.liveness_score,
        auto_approved=kyc_job.auto_approved
    )

@router.post("/verify/{ticket_id}", response_model=KYCVerificationResult)
async def verify_kyc_completion(
    ticket_id: UUID,
    db: Session = Depends(get_db),
) -> Any:
    """
    Verify KYC completion and return detailed results.
    """
    kyc_job = db.query(KYCJob).filter(KYCJob.ticket_id == ticket_id).first()
    if not kyc_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC job not found",
        )
    
    # Check verification status
    verified = kyc_job.status == "passed"
    tier_achieved = kyc_job.kyc_tier if verified else 0
    
    # Calculate confidence score
    confidence_score = kyc_job.risk_score or 0
    
    # Check which verification steps passed
    checks_passed = {
        "document_verification": kyc_job.ocr_json is not None and kyc_job.ocr_json.get("overall_confidence", 0) > 0.5,
        "face_matching": kyc_job.face_score is not None and kyc_job.face_score > 0.7,
        "liveness_detection": kyc_job.liveness_score is not None and kyc_job.liveness_score > 0.6,
        "risk_assessment": kyc_job.risk_score is not None and kyc_job.risk_score > 0.6
    }
    
    details = {
        "processing_time_hours": (
            (kyc_job.reviewed_at - kyc_job.submitted_at).total_seconds() / 3600
            if kyc_job.reviewed_at else None
        ),
        "auto_approved": kyc_job.auto_approved,
        "manual_review_required": kyc_job.status == "manual_review"
    }
    
    return KYCVerificationResult(
        verified=verified,
        tier_achieved=tier_achieved,
        confidence_score=confidence_score,
        checks_passed=checks_passed,
        details=details
    )

@router.get("/contract-status/{user_address}", response_model=SmartContractStatus)
async def get_smart_contract_status(
    user_address: str,
    db: Session = Depends(get_db),
) -> Any:
    """
    Get KYC status from smart contract for withdrawal eligibility.
    """
    if not contract_service.is_valid_address(user_address):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Ethereum address",
        )
    
    # Check smart contract status
    contract_status = await contract_service.check_kyc_status(user_address)
    
    if not contract_status['success']:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to check smart contract status",
        )
    
    # Check withdrawal eligibility
    eligibility = await contract_service.verify_withdrawal_eligibility(user_address, 0)
    
    return SmartContractStatus(
        user_address=user_address,
        kyc_tier=contract_status['tier'],
        approved=contract_status['approved'],
        withdrawal_eligible=eligibility['eligible'],
        last_updated=datetime.fromtimestamp(contract_status['timestamp'])
    )

@router.delete("/user/{user_id}/data")
async def delete_user_kyc_data(
    user_id: UUID,
    db: Session = Depends(get_db),
) -> Any:
    """
    Delete user KYC data for GDPR compliance (right to be forgotten).
    """
    # Find all KYC jobs for user
    kyc_jobs = db.query(KYCJob).filter(KYCJob.user_id == user_id).all()
    
    if not kyc_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No KYC data found for this user",
        )
    
    # Mark for deletion and anonymize
    for job in kyc_jobs:
        job.deletion_requested_at = datetime.utcnow()
        job.full_name = "DELETED"
        job.address = "DELETED"
        job.email = "DELETED"
        job.phone = "DELETED"
        job.encrypted_data = None
        job.ocr_json = None
    
    # Create audit log
    audit_log = AuditLog(
        action="gdpr_data_deletion",
        user_id=user_id,
        kyc_job_id=None,
        timestamp=datetime.utcnow(),
        details={
            "reason": "user_requested_deletion",
            "jobs_affected": len(kyc_jobs)
        }
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "message": "KYC data deletion completed",
        "jobs_affected": len(kyc_jobs)
    } 