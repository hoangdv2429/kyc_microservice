from celery import Celery
from app.core.config import settings
import os

# Use Redis as broker for minimal setup (no RabbitMQ required)
broker_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
result_backend = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

# Create Celery app
celery_app = Celery(
    "kyc_worker",
    broker=broker_url,
    backend=result_backend,
    include=["app.workers.tasks"]
)

# Development mode - run tasks synchronously
if os.getenv('CELERY_ALWAYS_EAGER', 'false').lower() == 'true':
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    print("🔧 Celery running in EAGER mode (synchronous tasks)")
else:
    print(f"🔧 Celery using Redis broker: {broker_url}")

# Basic Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=60 * 60 * 24,  # 24 hours
    broker_connection_retry_on_startup=True,
) 