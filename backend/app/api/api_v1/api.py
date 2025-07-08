from fastapi import APIRouter

from app.api.api_v1.endpoints import kyc, admin, upload, file_upload

api_router = APIRouter()

api_router.include_router(kyc.router, prefix="/kyc", tags=["kyc"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"]) 
api_router.include_router(file_upload.router, prefix="/files", tags=["file-upload"]) 