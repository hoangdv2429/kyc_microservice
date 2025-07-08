from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.minio_client import get_internal_minio_client, get_external_minio_client
from app.core.config import settings
from datetime import timedelta
import uuid
from typing import Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class PresignedURLRequest(BaseModel):
    file_type: str  # 'id_front', 'id_back', 'selfie'
    content_type: str = "image/jpeg"

class PresignedURLResponse(BaseModel):
    upload_url: str
    file_url: str
    object_name: str

@router.post("/presigned-url", response_model=PresignedURLResponse)
async def get_presigned_upload_url(request: PresignedURLRequest) -> PresignedURLResponse:
    """Generate presigned URL for file upload to MinIO"""
    try:
        # Validate file type
        allowed_types = ['id_front', 'id_back', 'selfie']
        if request.file_type not in allowed_types:
            logger.warning(f"Invalid file type received: {request.file_type}. Allowed: {allowed_types}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {request.file_type}. Allowed: {allowed_types}"
            )
        
        # Validate content type
        allowed_content_types = ['image/jpeg', 'image/png', 'image/jpg']
        if request.content_type not in allowed_content_types:
            logger.warning(f"Invalid content type received: {request.content_type}. Allowed: {allowed_content_types}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {request.content_type}. Allowed: {allowed_content_types}"
            )
        
        # Ensure bucket exists using internal client
        internal_client = get_internal_minio_client()
        if not internal_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            internal_client.make_bucket(settings.MINIO_BUCKET_NAME)
        
        # Create a special MinIO client that uses the external endpoint for presigned URLs
        # This allows the signatures to be valid when accessed from the browser
        from minio import Minio
        
        logger.info(f"Using internal endpoint: {settings.internal_minio_endpoint}")
        logger.info(f"Using external endpoint: {settings.external_minio_endpoint}")
        
        # Create a client that connects internally but generates URLs for external access
        # We'll connect to MinIO through the Docker host network
        try:
            # Create external client using host.docker.internal to reach host's localhost
            external_client = Minio(
                "host.docker.internal:9000",  # How container reaches host
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # Generate unique filename
            file_extension = request.content_type.split('/')[-1]
            if file_extension == 'jpeg':
                file_extension = 'jpg'
            
            filename = f"{request.file_type}_{uuid.uuid4()}.{file_extension}"
            object_name = f"uploads/{filename}"
            
            logger.info(f"Generating presigned URL for {request.file_type}: {object_name}")
            
            # Generate presigned URL using external client
            presigned_url = external_client.presigned_put_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=object_name,
                expires=timedelta(hours=1)
            )
            
            # Replace host.docker.internal with localhost for browser access
            browser_url = presigned_url.replace(
                "host.docker.internal:9000",
                "localhost:9000"
            )
            
        except Exception as e:
            logger.error(f"Failed to create external client, falling back to internal: {e}")
            # Fallback to internal client approach
            presigned_url = internal_client.presigned_put_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=object_name,
                expires=timedelta(hours=1)
            )
            browser_url = presigned_url.replace(
                f"http://{settings.internal_minio_endpoint}",
                f"http://{settings.external_minio_endpoint}"
            )
        
        # Generate final object URL using external endpoint
        protocol = "https" if settings.MINIO_SECURE else "http"
        final_url = f"{protocol}://{settings.external_minio_endpoint}/{settings.MINIO_BUCKET_NAME}/{object_name}"
        
        logger.info(f"Generated presigned URL for {request.file_type}: {object_name}")
        
        return PresignedURLResponse(
            upload_url=browser_url,
            file_url=final_url,
            object_name=object_name
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")

@router.get("/health")
async def upload_health_check():
    """Check if upload service is healthy"""
    try:
        minio_client = get_minio_client()
        # Simple health check - verify bucket exists
        bucket_exists = minio_client.bucket_exists(settings.MINIO_BUCKET_NAME)
        return {
            "status": "healthy" if bucket_exists else "unhealthy",
            "bucket_exists": bucket_exists,
            "bucket_name": settings.MINIO_BUCKET_NAME
        }
    except Exception as e:
        logger.error(f"Upload health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
