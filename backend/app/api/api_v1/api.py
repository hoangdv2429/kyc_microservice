from fastapi import APIRouter

from app.api.api_v1.endpoints import kyc, admin

api_router = APIRouter()

api_router.include_router(kyc.router, prefix="/kyc", tags=["kyc"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"]) 