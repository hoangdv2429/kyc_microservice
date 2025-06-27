from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app with scheduled tasks
celery_app = Celery(
    "kyc_worker",
    broker=f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}//",
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    include=["app.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=60 * 60 * 24,  # 24 hours
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    beat_schedule_filename="/app/celerybeat/celerybeat-schedule",
)

# Configure periodic tasks for compliance and maintenance
celery_app.conf.beat_schedule = {
    # Cleanup expired KYC data daily at 2 AM
    'cleanup-expired-kyc-data': {
        'task': 'app.workers.tasks.cleanup_expired_data',
        'schedule': crontab(hour=2, minute=0),
    },
    
    # Generate compliance reports weekly on Sundays at 3 AM
    'generate-compliance-reports': {
        'task': 'app.workers.tasks.generate_compliance_report',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
    },
    
    # Health check every 5 minutes
    'system-health-check': {
        'task': 'app.workers.tasks.system_health_check',
        'schedule': crontab(minute='*/5'),
    },
    
    # Process pending blockchain updates every hour
    'process-blockchain-updates': {
        'task': 'app.workers.tasks.process_pending_contract_updates',
        'schedule': crontab(minute=0),
    },
    
    # Archive old audit logs monthly
    'archive-audit-logs': {
        'task': 'app.workers.tasks.archive_old_audit_logs',
        'schedule': crontab(hour=1, minute=0, day_of_month=1),
    }
}

# Task routes for different types of work
celery_app.conf.task_routes = {
    "app.workers.tasks.process_kyc": {"queue": "kyc-processing"},
    "app.workers.tasks.run_advanced_ocr": {"queue": "ocr-processing"},
    "app.workers.tasks.run_face_analysis": {"queue": "face-processing"},
    "app.workers.tasks.send_notifications": {"queue": "notifications"},
    "app.workers.tasks.cleanup_expired_data": {"queue": "maintenance"},
    "app.workers.tasks.generate_compliance_report": {"queue": "maintenance"},
    "app.workers.tasks.system_health_check": {"queue": "monitoring"},
    "app.workers.tasks.process_pending_contract_updates": {"queue": "blockchain"},
    "app.workers.tasks.archive_old_audit_logs": {"queue": "maintenance"},
}

celery_app.conf.timezone = 'UTC' 