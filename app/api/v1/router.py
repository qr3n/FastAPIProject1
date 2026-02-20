# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import dishes, auth, businesses, tables, business_media, barbers


api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(businesses.router)
api_router.include_router(dishes.router)
api_router.include_router(tables.router)
api_router.include_router(business_media.router)
api_router.include_router(barbers.router)