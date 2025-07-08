from minio import Minio
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

_internal_minio_client = None
_external_minio_client = None

def get_internal_minio_client() -> Minio:
    """Get MinIO client for backend-to-MinIO operations (using internal endpoint)"""
    global _internal_minio_client
    
    if _internal_minio_client is None:
        try:
            _internal_minio_client = Minio(
                settings.internal_minio_endpoint,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # Ensure bucket exists
            if not _internal_minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
                _internal_minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
                logger.info(f"Created bucket: {settings.MINIO_BUCKET_NAME}")
                
        except Exception as e:
            logger.error(f"Failed to initialize internal MinIO client: {e}")
            raise
    
    return _internal_minio_client

def get_external_minio_client() -> Minio:
    """Get MinIO client for frontend-facing operations (using external endpoint)"""
    global _external_minio_client
    
    if _external_minio_client is None:
        try:
            _external_minio_client = Minio(
                settings.external_minio_endpoint,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
                
        except Exception as e:
            logger.error(f"Failed to initialize external MinIO client: {e}")
            raise
    
    return _external_minio_client

def get_minio_client() -> Minio:
    """Default to internal client for backward compatibility"""
    return get_internal_minio_client()

def cleanup_minio_client():
    """Cleanup MinIO clients (for testing)"""
    global _internal_minio_client, _external_minio_client
    _internal_minio_client = None
    _external_minio_client = None
