from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.core.minio_client import get_internal_minio_client
from app.core.config import settings
from typing import Optional
import uuid
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

router = APIRouter()

class FileUploadResponse(BaseModel):
    success: bool
    file_url: str
    object_name: str
    file_size: int
    message: str

@router.post("/file", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(...)
) -> FileUploadResponse:
    """
    Upload file directly through backend proxy to MinIO.
    This avoids presigned URL signature issues with hostname differences.
    """
    try:
        # Validate file type
        allowed_types = ['id_front', 'id_back', 'selfie']
        if file_type not in allowed_types:
            logger.warning(f"Invalid file type received: {file_type}. Allowed: {allowed_types}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type: {file_type}. Allowed: {allowed_types}"
            )
        
        # Validate content type
        allowed_content_types = ['image/jpeg', 'image/png', 'image/jpg']
        if file.content_type and file.content_type not in allowed_content_types:
            logger.warning(f"Invalid content type received: {file.content_type}. Allowed: {allowed_content_types}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {file.content_type}. Allowed: {allowed_content_types}"
            )
        
        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > max_size:
            logger.warning(f"File too large: {file_size} bytes (max: {max_size})")
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file not allowed"
            )
        
        # Generate unique filename
        file_extension = 'jpg'
        if file.content_type == 'image/png':
            file_extension = 'png'
        elif file.filename and '.' in file.filename:
            file_extension = file.filename.split('.')[-1].lower()
        
        filename = f"{file_type}_{uuid.uuid4()}.{file_extension}"
        object_name = f"uploads/{filename}"
        
        logger.info(f"Uploading {file_type} file: {object_name} ({file_size} bytes)")
        
        # Get MinIO client
        minio_client = get_internal_minio_client()
        
        # Ensure bucket exists
        if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
            logger.info(f"Created bucket: {settings.MINIO_BUCKET_NAME}")
        
        # Upload file to MinIO
        file_stream = BytesIO(file_content)
        
        minio_client.put_object(
            bucket_name=settings.MINIO_BUCKET_NAME,
            object_name=object_name,
            data=file_stream,
            length=file_size,
            content_type=file.content_type or f'image/{file_extension}'
        )
        
        # Generate file URL
        protocol = "https" if settings.MINIO_SECURE else "http"
        file_url = f"{protocol}://{settings.external_minio_endpoint}/{settings.MINIO_BUCKET_NAME}/{object_name}"
        
        logger.info(f"Successfully uploaded {file_type}: {object_name}")
        
        return FileUploadResponse(
            success=True,
            file_url=file_url,
            object_name=object_name,
            file_size=file_size,
            message=f"File {file_type} uploaded successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to upload file: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/health")
async def file_upload_health_check():
    """Check if file upload service is healthy"""
    try:
        minio_client = get_internal_minio_client()
        # Simple health check - verify bucket exists
        bucket_exists = minio_client.bucket_exists(settings.MINIO_BUCKET_NAME)
        return {
            "status": "healthy" if bucket_exists else "unhealthy",
            "bucket_exists": bucket_exists,
            "bucket_name": settings.MINIO_BUCKET_NAME,
            "upload_method": "backend_proxy"
        }
    except Exception as e:
        logger.error(f"File upload health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "upload_method": "backend_proxy"
        }

@router.delete("/file/{object_name:path}")
async def delete_file(object_name: str):
    """Delete a file from MinIO (for cleanup/testing purposes)"""
    try:
        minio_client = get_internal_minio_client()
        
        # Validate object name format
        if not object_name.startswith('uploads/'):
            raise HTTPException(
                status_code=400,
                detail="Can only delete files in uploads/ directory"
            )
        
        # Check if file exists
        try:
            minio_client.stat_object(settings.MINIO_BUCKET_NAME, object_name)
        except Exception:
            raise HTTPException(
                status_code=404,
                detail="File not found"
            )
        
        # Delete the file
        minio_client.remove_object(settings.MINIO_BUCKET_NAME, object_name)
        
        logger.info(f"Successfully deleted file: {object_name}")
        
        return {
            "success": True,
            "message": f"File {object_name} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {object_name}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete file: {str(e)}"
        )
