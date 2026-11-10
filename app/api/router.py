from fastapi import APIRouter
from app.api.citizen import router as citizen_router
from app.api.official import router as official_router

api_router = APIRouter()

# Include citizen routes
api_router.include_router(citizen_router)

# Include official routes
api_router.include_router(official_router)

