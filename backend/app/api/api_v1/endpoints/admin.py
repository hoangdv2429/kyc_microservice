from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.kyc_job import KYCJob
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.admin import (
    KYCJobAdmin, KYCReviewRequest, KYCStats, 
    AdminDashboard, AuditLogResponse, KYCReview, PendingKYC
)
from app.services.email_service import EmailService
from app.services.telegram_service import TelegramService
from app.services.contract_service import SmartContractService
from app.utils.encryption import encryption

router = APIRouter()

email_service = EmailService()
telegram_service = TelegramService()
contract_service = SmartContractService()

@router.get("/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(
    db: Session = Depends(get_db),
) -> Any:
    """Get admin dashboard with KYC statistics."""
    
    # Get overall statistics
    total_submissions = db.query(KYCJob).count()
    pending_reviews = db.query(KYCJob).filter(KYCJob.status == "manual_review").count()
    passed_kyc = db.query(KYCJob).filter(KYCJob.status == "passed").count()
    rejected_kyc = db.query(KYCJob).filter(KYCJob.status == "rejected").count()
    
    # Get statistics by tier
    tier_stats = db.query(
        KYCJob.kyc_tier,
        func.count(KYCJob.kyc_tier)
    ).filter(
        KYCJob.status == "passed"
    ).group_by(KYCJob.kyc_tier).all()
    
    # Get recent submissions (last 7 days)
    from datetime import timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_submissions = db.query(func.count(KYCJob.ticket_id)).filter(
        KYCJob.submitted_at >= week_ago
    ).scalar()
    
    # Get average processing time
    completed_jobs = db.query(KYCJob).filter(
        KYCJob.reviewed_at.isnot(None)
    ).all()
    
    avg_processing_time = 0
    if completed_jobs:
        total_time = sum([
            (job.reviewed_at - job.submitted_at).total_seconds() / 3600  # in hours
            for job in completed_jobs
        ])
        avg_processing_time = total_time / len(completed_jobs)
    
    return AdminDashboard(
        total_submissions=total_submissions,
        pending_reviews=pending_reviews,
        passed_kyc=passed_kyc,
        rejected_kyc=rejected_kyc,
        tier_0_count=sum([count for tier, count in tier_stats if tier == 0]),
        tier_1_count=sum([count for tier, count in tier_stats if tier == 1]),
        tier_2_count=sum([count for tier, count in tier_stats if tier == 2]),
        recent_submissions_7d=recent_submissions,
        avg_processing_time_hours=avg_processing_time,
        approval_rate=(passed_kyc / total_submissions * 100) if total_submissions > 0 else 0
    )

@router.get("/pending", response_model=List[PendingKYC])
async def list_pending_kyc(
    *,
    db: Session = Depends(get_db),
    limit: int = Query(default=10, le=100),
) -> Any:
    """
    List pending KYC verification requests.
    """
    pending_jobs = (
        db.query(KYCJob)
        .filter(KYCJob.status.in_(["pending", "manual_review"]))
        .order_by(KYCJob.submitted_at.desc())
        .limit(limit)
        .all()
    )
    return pending_jobs

@router.post("/review/{ticket_id}", response_model=dict[str, bool])
async def review_kyc(
    *,
    db: Session = Depends(get_db),
    ticket_id: UUID,
    review: KYCReview,
) -> Any:
    """
    Review a KYC verification request.
    """
    kyc_job = db.query(KYCJob).filter(KYCJob.ticket_id == ticket_id).first()
    if not kyc_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KYC job not found",
        )
    
    if kyc_job.status not in ["pending", "manual_review"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="KYC job is not pending review",
        )
    
    # Map frontend decision to backend status
    status_mapping = {
        "approved": "passed",
        "rejected": "rejected",
        "passed": "passed"
    }
    final_status = status_mapping.get(review.decision, review.decision)
    
    # TODO on production should be already created by other services
    # Create or get reviewer user if not exists
    reviewer = db.query(User).filter(User.id == review.reviewer_id).first()
    if not reviewer:
        reviewer = User(
            id=review.reviewer_id,
            email=f"admin.{review.reviewer_id}@echofi.com",
            phone=None
        )
        db.add(reviewer)
        db.commit()
        db.refresh(reviewer)
    
    kyc_job.status = final_status
    kyc_job.reviewer_id = review.reviewer_id
    kyc_job.reviewed_at = datetime.utcnow()
    kyc_job.note = review.note
    kyc_job.kyc_tier = 2 if final_status == "passed" else 0
    kyc_job.auto_approved = False
    
    db.commit()
    
    # Create audit log
    audit_log = AuditLog(
        action="manual_review",
        user_id=kyc_job.user_id,
        kyc_job_id=kyc_job.ticket_id,
        timestamp=datetime.utcnow(),
        details={
            "reviewer_id": str(review.reviewer_id),
            "decision": final_status,
            "note": review.note
        }
    )
    db.add(audit_log)
    db.commit()
    
    return {"updated": True}

@router.get("/kyc-jobs", response_model=List[KYCJobAdmin])
async def get_kyc_jobs(
    *,
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status"),
    tier: Optional[int] = Query(None, description="Filter by KYC tier"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> Any:
    """Get list of KYC jobs for admin review."""
    
    query = db.query(KYCJob)
    
    # Apply filters
    if status:
        query = query.filter(KYCJob.status == status)
    if tier is not None:
        query = query.filter(KYCJob.kyc_tier == tier)
    
    # Order by submission date (newest first)
    query = query.order_by(desc(KYCJob.submitted_at))
    
    # Apply pagination
    kyc_jobs = query.offset(skip).limit(limit).all()
    
    # Convert to response format
    result = []
    for job in kyc_jobs:
        job_dict = {
            "ticket_id": job.ticket_id,
            "user_id": job.user_id,
            "status": job.status,
            "kyc_tier": job.kyc_tier,
            "submitted_at": job.submitted_at,
            "reviewed_at": job.reviewed_at,
            "reviewer_id": job.reviewer_id,
            "note": job.note,
            "risk_score": job.risk_score,
            "face_score": job.face_score,
            "liveness_score": job.liveness_score,
            "auto_approved": job.auto_approved,
            # Decrypt sensitive data for admin
            "full_name": job.full_name,
            "email": job.email,
            "phone": job.phone,
            "address": job.address,
            "dob": job.dob
        }
        result.append(job_dict)
    
    return result

@router.get("/stats", response_model=KYCStats)
async def get_kyc_stats(
    *,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days for statistics")
) -> Any:
    """Get KYC statistics for the specified time period."""
    
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get submissions in time period
    submissions = db.query(KYCJob).filter(
        KYCJob.submitted_at >= start_date
    ).all()
    
    # Calculate statistics
    total_submissions = len(submissions)
    auto_approved = len([j for j in submissions if j.auto_approved and j.status == "passed"])
    manual_reviewed = len([j for j in submissions if not j.auto_approved and j.status in ["passed", "rejected"]])
    pending = len([j for j in submissions if j.status in ["pending", "processing", "manual_review"]])
    
    # Calculate average scores
    face_scores = [j.face_score for j in submissions if j.face_score is not None]
    liveness_scores = [j.liveness_score for j in submissions if j.liveness_score is not None]
    risk_scores = [j.risk_score for j in submissions if j.risk_score is not None]
    
    return KYCStats(
        period_days=days,
        total_submissions=total_submissions,
        auto_approved=auto_approved,
        manual_reviewed=manual_reviewed,
        pending=pending,
        avg_face_score=sum(face_scores) / len(face_scores) if face_scores else 0,
        avg_liveness_score=sum(liveness_scores) / len(liveness_scores) if liveness_scores else 0,
        avg_risk_score=sum(risk_scores) / len(risk_scores) if risk_scores else 0,
        processing_time_avg=0  # TODO: Calculate from audit logs
    ) 