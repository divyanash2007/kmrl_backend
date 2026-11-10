from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.models import Base
from app.schemas.common import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "Kochi Metro Rail Limited (KMRL) AI-Powered Civic Service & Grievance Redressal System.\n\n"
        "Features:\n"
        "- Location-agnostic ticket submission with optional GPS authenticity & emergency reach.\n"
        "- AI Classifier & Rule-based Priority Engine.\n"
        "- Grounded RAG Knowledge Base.\n"
        "- Official Safe-Key Management & Escalation Triage."
    ),
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API Routes
from app.api.router import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)



@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health Check & Database Connectivity",
)
def health_check(db: Session = Depends(get_db)):
    """Verifies that the API service is alive and the PostgreSQL database responds."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"unreachable: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity check failed: {str(e)}",
        )

    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version="1.0.0",
        database=db_status,
    )


@app.get("/", tags=["System"], summary="API Root")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
    }
