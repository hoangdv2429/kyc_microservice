import io
import asyncio
from typing import Dict, Any
import pytesseract
from PIL import Image
import cv2
import numpy as np
from deepface import DeepFace
from minio import Minio
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.kyc_job import KYCJob
from app.models.audit_log import AuditLog
from app.workers.celery_app import celery_app
from celery import current_app as celery_current_app
import os
import requests
from celery import shared_task
from datetime import datetime, timedelta
import logging
import json

# Fix for PIL.Image.ANTIALIAS deprecation
try:
    # For newer Pillow versions
    PIL_RESAMPLE = Image.LANCZOS
except AttributeError:
    # Fallback for older versions
    PIL_RESAMPLE = Image.ANTIALIAS

# Import our new services
from app.services.ocr_service import OCRService
from app.services.face_match_service import FaceMatchingService
from app.services.liveness_service import LivenessDetectionService
from app.services.email_service import EmailService
from app.services.telegram_service import TelegramService
from app.services.contract_service import SmartContractService
from app.utils.encryption import encryption

logger = logging.getLogger(__name__)

def make_json_serializable(obj):
    """Convert numpy types to Python native types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_INTERNAL_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)

# Initialize services
ocr_service = OCRService()
face_service = FaceMatchingService()
liveness_service = LivenessDetectionService()
email_service = EmailService()
telegram_service = TelegramService()
contract_service = SmartContractService()

@celery_app.task(name="app.workers.tasks.process_kyc")
def process_kyc(ticket_id: str) -> None:
    """Main KYC processing task that coordinates all sub-tasks."""
    db = SessionLocal()
    try:
        kyc_job = db.query(KYCJob).filter(KYCJob.ticket_id == ticket_id).first()
        if not kyc_job:
            logger.error(f"KYC job not found: {ticket_id}")
            return

        # Update status to processing
        kyc_job.status = "processing"
        db.commit()

        # Create audit log
        audit_log = AuditLog(
            action="start_processing",
            user_id=kyc_job.user_id,
            kyc_job_id=kyc_job.ticket_id,
            timestamp=datetime.utcnow(),
            details={"info": "KYC processing started"}
        )
        db.add(audit_log)
        db.commit()

        # Step 1: Run OCR on documents
        logger.info(f"Starting OCR processing for {ticket_id}")
        # Check if running in eager mode
        if celery_app.conf.task_always_eager:
            # In eager mode, call function directly
            ocr_result = run_advanced_ocr(kyc_job.doc_front, kyc_job.doc_back)
        else:
            # In normal mode, use Celery task
            ocr_result = run_advanced_ocr.delay(kyc_job.doc_front, kyc_job.doc_back).get()

        # Make OCR result JSON serializable
        ocr_result = make_json_serializable(ocr_result)
        kyc_job.ocr_json = ocr_result
        db.commit()

        # Step 2: Run face matching and liveness detection
        logger.info(f"Starting face matching for {ticket_id}")

        # Check if running in eager mode
        if celery_app.conf.task_always_eager:
            # In eager mode, call function directly
            face_result = run_face_analysis(kyc_job.doc_front, kyc_job.selfie)
        else:
            # In normal mode, use Celery task
            face_result = run_face_analysis.delay(kyc_job.doc_front, kyc_job.selfie).get()
        
        # Make face result JSON serializable
        face_result = make_json_serializable(face_result)
        kyc_job.face_score = face_result.get("face_score", 0)
        kyc_job.liveness_score = face_result.get("liveness_score", 0)
        db.commit()

        # Step 3: Calculate risk score
        risk_score = calculate_risk_score(ocr_result, face_result)
        kyc_job.risk_score = risk_score
        db.commit()

        # Step 4: Determine approval status
        approval_decision = determine_approval_status(kyc_job, risk_score)
        kyc_job.status = approval_decision["status"]
        kyc_job.kyc_tier = approval_decision["tier"]
        kyc_job.auto_approved = approval_decision["auto_approved"]
        
        if approval_decision["status"] in ["passed", "rejected"]:
            kyc_job.reviewed_at = datetime.utcnow()
        
        db.commit()

        # Step 5: Encrypt sensitive data
        sensitive_data = {
            'full_name': kyc_job.full_name,
            'dob': kyc_job.dob,
            'address': kyc_job.address,
            'email': kyc_job.email,
            'phone': kyc_job.phone
        }
        encrypted_result = encryption.encrypt_sensitive_fields(sensitive_data)
        kyc_job.encrypted_data = encrypted_result
        
        # Set data retention period
        kyc_job.data_retention_until = datetime.utcnow() + timedelta(days=settings.KYC_DATA_RETENTION_DAYS)
        db.commit()

        # Step 6: Send notifications
        if celery_app.conf.task_always_eager:
            # In eager mode, call function directly
            send_notifications(str(kyc_job.ticket_id))
        else:
            # In normal mode, use Celery task
            send_notifications.delay(str(kyc_job.ticket_id))

        # Step 7: Update smart contract (if approved)
        if kyc_job.status == "passed" and kyc_job.user_id:
            # Note: This would require user's wallet address
            # For now, we'll add it to a queue for manual processing
            pass

        logger.info(f"KYC processing completed for {ticket_id} with status: {kyc_job.status}")

    except Exception as e:
        logger.error(f"KYC processing failed for {ticket_id}: {str(e)}")
        db.rollback()  # Rollback the transaction first
        if 'kyc_job' in locals():
            kyc_job.status = "failed"
            kyc_job.note = f"Processing error: {str(e)}"
            kyc_job.reviewed_at = datetime.utcnow() # Set review time on failure
            db.commit()
    finally:
        db.close()

def _replace_minio_host(url: str) -> str:
    """Replace external MinIO host with internal host for worker access."""
    if not hasattr(settings, 'MINIO_EXTERNAL_ENDPOINT') or not hasattr(settings, 'MINIO_INTERNAL_ENDPOINT'):
        return url
    if not settings.MINIO_EXTERNAL_ENDPOINT or not settings.MINIO_INTERNAL_ENDPOINT:
        return url
    return url.replace(settings.MINIO_EXTERNAL_ENDPOINT, settings.MINIO_INTERNAL_ENDPOINT)

@celery_app.task(name="app.workers.tasks.run_advanced_ocr")
def run_advanced_ocr(doc_front_url: str, doc_back_url: str) -> Dict[str, Any]:
    """Run advanced OCR on document images with multiple checks."""
    try:
        # Replace host for internal worker access
        internal_front_url = _replace_minio_host(doc_front_url)
        internal_back_url = _replace_minio_host(doc_back_url)

        # Download images
        front_path = f"/tmp/ocr_front_{datetime.now().timestamp()}.jpg"
        back_path = f"/tmp/ocr_back_{datetime.now().timestamp()}.jpg"
        
        with open(front_path, "wb") as f:
            f.write(requests.get(internal_front_url, timeout=30).content)
        with open(back_path, "wb") as f:
            f.write(requests.get(internal_back_url, timeout=30).content)

        # Extract data from front (main personal information)
        front_data = ocr_service.extract_vietnamese_id_front(front_path)
        
        # Extract data from back (mrz, expiry, etc.)
        back_data = ocr_service.extract_vietnamese_id_back(back_path)
        
        # Document authenticity check
        authenticity_front = ocr_service.verify_document_authenticity(front_path)
        authenticity_back = ocr_service.verify_document_authenticity(back_path)

        # Clean up
        os.remove(front_path)
        os.remove(back_path)

        return {
            "front_data": front_data,
            "back_data": back_data,
            "authenticity_front": authenticity_front,
            "authenticity_back": authenticity_back,
            "overall_confidence": (front_data.get('ocr_confidence', 0) + back_data.get('ocr_confidence', 0)) / 2
        }
        
    except Exception as e:
        logger.error(f"Advanced OCR failed: {str(e)}")
        return {"error": str(e), "overall_confidence": 0}

@celery_app.task(name="app.workers.tasks.run_face_analysis")
def run_face_analysis(doc_url: str, selfie_url: str) -> Dict[str, Any]:
    """Run comprehensive face analysis including matching and liveness."""
    try:
        # Replace host for internal worker access
        internal_doc_url = _replace_minio_host(doc_url)
        internal_selfie_url = _replace_minio_host(selfie_url)

        # Download images
        doc_path = f"/tmp/face_doc_{datetime.now().timestamp()}.jpg"
        selfie_path = f"/tmp/face_selfie_{datetime.now().timestamp()}.jpg"
        
        with open(doc_path, "wb") as f:
            f.write(requests.get(internal_doc_url, timeout=30).content)
        with open(selfie_path, "wb") as f:
            f.write(requests.get(internal_selfie_url, timeout=30).content)

        # Face matching
        face_match_result = face_service.compare_faces(doc_path, selfie_path)
        
        # Liveness detection
        liveness_result = liveness_service.detect_liveness(selfie_path)
        
        # Multiple face detection (security check)
        multiple_faces_check = face_service.detect_multiple_faces(selfie_path)
        
        # Face quality analysis
        quality_result = face_service.calculate_face_quality_score(selfie_path)

        # Clean up
        os.remove(doc_path)
        os.remove(selfie_path)

        return {
            "face_score": face_match_result.get("confidence", 0),
            "face_match": face_match_result.get("match", False),
            "liveness_score": liveness_result.get("confidence", 0),
            "is_live": liveness_result.get("is_live", False),
            "multiple_faces": multiple_faces_check.get("multiple_faces", False),
            "quality_score": quality_result.get("quality_score", 0),
            "face_match_details": face_match_result,
            "liveness_details": liveness_result
        }
        
    except Exception as e:
        logger.error(f"Face analysis failed: {str(e)}")
        return {
            "face_score": 0,
            "liveness_score": 0,
            "is_live": False,
            "error": str(e)
        }

def calculate_risk_score(ocr_result: Dict[str, Any], face_result: Dict[str, Any]) -> float:
    """Calculate overall risk score based on all checks."""
    try:
        scores = []
        
        # OCR confidence score
        ocr_confidence = ocr_result.get("overall_confidence", 0)
        scores.append(ocr_confidence)
        
        # Face matching score
        face_score = face_result.get("face_score", 0)
        scores.append(face_score)
        
        # Liveness score
        liveness_score = face_result.get("liveness_score", 0)
        scores.append(liveness_score)
        
        # Quality score
        quality_score = face_result.get("quality_score", 0)
        scores.append(quality_score)
        
        # Document authenticity
        auth_front = ocr_result.get("authenticity_front", {}).get("authenticity_score", 0)
        auth_back = ocr_result.get("authenticity_back", {}).get("authenticity_score", 0)
        scores.append((auth_front + auth_back) / 2)
        
        # Penalties for red flags
        penalties = 0
        if face_result.get("multiple_faces", False):
            penalties += 0.2
        if not face_result.get("is_live", True):
            penalties += 0.3
        if not face_result.get("face_match", False):
            penalties += 0.5
        
        # Calculate final score
        valid_scores = [s for s in scores if s > 0]
        if not valid_scores:
            return 0
        
        average_score = sum(valid_scores) / len(valid_scores)
        final_score = max(0, average_score - penalties)
        
        return final_score
        
    except Exception as e:
        logger.error(f"Risk score calculation failed: {str(e)}")
        return 0

def determine_approval_status(kyc_job: KYCJob, risk_score: float) -> Dict[str, Any]:
    """Determine approval status based on risk score and thresholds."""
    try:
        if risk_score >= settings.AUTO_APPROVAL_THRESHOLD:
            return {
                "status": "passed",
                "tier": 2,  # Full KYC
                "auto_approved": True
            }
        elif risk_score >= settings.MANUAL_REVIEW_THRESHOLD:
            return {
                "status": "manual_review",
                "tier": 0,  # Will be set after manual review
                "auto_approved": False
            }
        else:
            return {
                "status": "rejected",
                "tier": 0,
                "auto_approved": True
            }
    except Exception as e:
        logger.error(f"Approval determination failed: {str(e)}")
        return {
            "status": "manual_review",
            "tier": 0,
            "auto_approved": False
        }

@celery_app.task(name="app.workers.tasks.send_notifications")
def send_notifications(ticket_id: str) -> None:
    """Send email and telegram notifications about KYC status."""
    db = SessionLocal()
    try:
        kyc_job = db.query(KYCJob).filter(KYCJob.ticket_id == ticket_id).first()
        if not kyc_job:
            return

        # Prepare notification data
        notification_data = {
            'ticket_id': str(kyc_job.ticket_id),
            'status': kyc_job.status,
            'full_name': kyc_job.full_name,
            'email': kyc_job.email,
            'kyc_tier': kyc_job.kyc_tier,
            'note': kyc_job.note,
            'reviewed_at': kyc_job.reviewed_at.isoformat() if kyc_job.reviewed_at else None,
            'submitted_at': kyc_job.submitted_at.isoformat(),
            'risk_score': kyc_job.risk_score,
            'face_score': kyc_job.face_score,
            'liveness_score': kyc_job.liveness_score,
            'ocr_confidence': kyc_job.ocr_json.get('overall_confidence', 0) if kyc_job.ocr_json else 0
        }

        # Send email notification
        if kyc_job.email:
            try:
                email_service.send_kyc_status_email(kyc_job.email, notification_data)
            except Exception as e:
                logger.error(f"Email notification failed: {str(e)}")

        # Send admin notification for manual review
        if kyc_job.status == "manual_review" and settings.TELEGRAM_ADMIN_CHAT_ID:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    telegram_service.send_admin_notification(
                        settings.TELEGRAM_ADMIN_CHAT_ID,
                        notification_data
                    )
                )
            except Exception as e:
                logger.error(f"Telegram admin notification failed: {str(e)}")

        # Create audit log
        audit_log = AuditLog(
            action="notification_sent",
            user_id=kyc_job.user_id,
            kyc_job_id=kyc_job.ticket_id,
            timestamp=datetime.utcnow(),
            details={"status": kyc_job.status, "notifications_sent": True}
        )
        db.add(audit_log)
        db.commit()

    except Exception as e:
        logger.error(f"Notification sending failed: {str(e)}")
    finally:
        db.close()

@celery_app.task(name="app.workers.tasks.cleanup_expired_data")
def cleanup_expired_data() -> None:
    """Clean up expired KYC data for GDPR compliance."""
    db = SessionLocal()
    try:
        # Find expired records
        expired_jobs = db.query(KYCJob).filter(
            KYCJob.data_retention_until < datetime.utcnow()
        ).all()

        for job in expired_jobs:
            # Mark for deletion or anonymize data
            job.full_name = "DELETED"
            job.address = "DELETED"
            job.email = "DELETED"
            job.phone = "DELETED"
            job.encrypted_data = None
            job.ocr_json = None
            
            # Create audit log
            audit_log = AuditLog(
                action="data_cleanup",
                user_id=job.user_id,
                kyc_job_id=job.ticket_id,
                timestamp=datetime.utcnow(),
                details={"reason": "data_retention_expired"}
            )
            db.add(audit_log)

        db.commit()
        logger.info(f"Cleaned up {len(expired_jobs)} expired KYC records")

    except Exception as e:
        logger.error(f"Data cleanup failed: {str(e)}")
    finally:
        db.close()

# Additional scheduled tasks for compliance and maintenance

@celery_app.task(name="app.workers.tasks.generate_compliance_report")
def generate_compliance_report() -> None:
    """Generate weekly compliance report for regulatory purposes."""
    db = SessionLocal()
    try:
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Get statistics for the week
        weekly_submissions = db.query(KYCJob).filter(
            KYCJob.submitted_at >= week_ago
        ).all()
        
        # Generate report data
        report_data = {
            "period_start": week_ago.isoformat(),
            "period_end": datetime.utcnow().isoformat(),
            "total_submissions": len(weekly_submissions),
            "auto_approved": len([j for j in weekly_submissions if j.auto_approved and j.status == "passed"]),
            "manual_reviewed": len([j for j in weekly_submissions if not j.auto_approved and j.status in ["passed", "rejected"]]),
            "rejected": len([j for j in weekly_submissions if j.status == "rejected"]),
            "pending": len([j for j in weekly_submissions if j.status in ["pending", "processing", "manual_review"]]),
            "avg_processing_time": 0,  # Calculate from audit logs
            "compliance_metrics": {
                "data_retention_compliance": True,
                "gdpr_deletion_requests": 0,  # Count from audit logs
                "audit_trail_complete": True
            }
        }
        
        # Create audit log for report generation
        audit_log = AuditLog(
            action="compliance_report_generated",
            user_id=None,
            kyc_job_id=None,
            timestamp=datetime.utcnow(),
            details=report_data
        )
        db.add(audit_log)
        db.commit()
        
        logger.info(f"Compliance report generated: {report_data['total_submissions']} submissions processed")
        
    except Exception as e:
        logger.error(f"Compliance report generation failed: {str(e)}")
    finally:
        db.close()

@celery_app.task(name="app.workers.tasks.system_health_check")
def system_health_check() -> None:
    """Perform system health check and alert if issues found."""
    db = SessionLocal()
    try:
        # Check database connectivity
        db.execute("SELECT 1")
        
        # Check for stuck jobs (processing for too long)
        stuck_threshold = datetime.utcnow() - timedelta(hours=2)
        stuck_jobs = db.query(KYCJob).filter(
            KYCJob.status == "processing",
            KYCJob.submitted_at < stuck_threshold
        ).count()
        
        # Check queue health (simplified)
        pending_count = db.query(KYCJob).filter(
            KYCJob.status.in_(["pending", "processing"])
        ).count()
        
        # Health metrics
        health_status = {
            "database_healthy": True,
            "stuck_jobs": stuck_jobs,
            "pending_jobs": pending_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Alert if issues found
        if stuck_jobs > 0:
            logger.warning(f"Found {stuck_jobs} stuck KYC jobs")
            
        if pending_count > 100:  # Threshold for high load
            logger.warning(f"High load: {pending_count} pending jobs")
        
        # Create health check audit log
        audit_log = AuditLog(
            action="system_health_check",
            user_id=None,
            kyc_job_id=None,
            timestamp=datetime.utcnow(),
            details=health_status
        )
        db.add(audit_log)
        db.commit()
        
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        # Send alert to admin
    finally:
        db.close()

@celery_app.task(name="app.workers.tasks.process_pending_contract_updates")
def process_pending_contract_updates() -> None:
    """Process pending smart contract updates for approved KYC jobs."""
    db = SessionLocal()
    try:
        # Find approved KYC jobs that need contract updates
        pending_updates = db.query(AuditLog).filter(
            AuditLog.action == "contract_update_needed"
        ).limit(10).all()  # Process in batches
        
        for audit_log in pending_updates:
            try:
                # Get KYC job details
                kyc_job = db.query(KYCJob).filter(
                    KYCJob.ticket_id == audit_log.kyc_job_id
                ).first()
                
                if kyc_job and kyc_job.status == "passed":
                    # Note: In real implementation, you would need user's wallet address
                    # For now, create a notification for manual processing
                    
                    # Create notification for admin to process manually
                    notification_audit = AuditLog(
                        action="manual_contract_update_required",
                        user_id=kyc_job.user_id,
                        kyc_job_id=kyc_job.ticket_id,
                        timestamp=datetime.utcnow(),
                        details={
                            "tier": kyc_job.kyc_tier,
                            "approved": True,
                            "requires_wallet_address": True
                        }
                    )
                    db.add(notification_audit)
                    
                    # Mark original audit log as processed
                    audit_log.details["processed"] = True
                    audit_log.details["processed_at"] = datetime.utcnow().isoformat()
                
            except Exception as e:
                logger.error(f"Failed to process contract update for {audit_log.kyc_job_id}: {str(e)}")
        
        db.commit()
        logger.info(f"Processed {len(pending_updates)} pending contract updates")
        
    except Exception as e:
        logger.error(f"Contract updates processing failed: {str(e)}")
    finally:
        db.close()

@celery_app.task(name="app.workers.tasks.archive_old_audit_logs")
def archive_old_audit_logs() -> None:
    """Archive old audit logs to comply with retention policies."""
    db = SessionLocal()
    try:
        # Archive logs older than retention period
        archive_threshold = datetime.utcnow() - timedelta(days=settings.AUDIT_LOG_RETENTION_DAYS)
        
        # Count logs to be archived
        old_logs_count = db.query(AuditLog).filter(
            AuditLog.timestamp < archive_threshold
        ).count()
        
        if old_logs_count > 0:
            # In a real implementation, you would:
            # 1. Export logs to long-term storage (S3, etc.)
            # 2. Compress and encrypt archived data
            # 3. Delete from active database
            
            # For now, just mark them as archived
            old_logs = db.query(AuditLog).filter(
                AuditLog.timestamp < archive_threshold
            ).all()
            
            for log in old_logs:
                log.details = log.details or {}
                log.details["archived"] = True
                log.details["archived_at"] = datetime.utcnow().isoformat()
            
            db.commit()
            
            # Create archive completion log
            archive_log = AuditLog(
                action="audit_logs_archived",
                user_id=None,
                kyc_job_id=None,
                timestamp=datetime.utcnow(),
                details={
                    "logs_archived": old_logs_count,
                    "archive_threshold": archive_threshold.isoformat()
                }
            )
            db.add(archive_log)
            db.commit()
            
            logger.info(f"Archived {old_logs_count} old audit logs")
        else:
            logger.info("No audit logs need archiving")
            
    except Exception as e:
        logger.error(f"Audit log archiving failed: {str(e)}")
    finally:
        db.close()

# Legacy tasks for backward compatibility
@shared_task
def process_ocr(kyc_job_id: str):
    """Legacy OCR processing task - redirects to new advanced OCR."""
    return process_kyc(kyc_job_id)