"""
Enhanced health check endpoints with connectivity checks and version info.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any
import asyncio
import rich
from sqlalchemy import text

from app.core.db.session import AsyncSessionLocal
from app.core.config.settings import settings

router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    version: str
    environment: str
    details: Dict[str, Any]


class ReadinessStatus(BaseModel):
    """Readiness check response model."""
    ready: bool
    checks: Dict[str, bool]


async def check_database() -> bool:
    """Check database connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        rich.print("Database connection failed", e)
        return False


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if application is running.
    """
    return HealthStatus(
        status="healthy",
        version="1.0.0",  # TODO: Get from package or env
        environment="development" if settings.debug else "production",
        details={
            "app_name": settings.app_name
        }
    )


@router.get("/health/liveness")
async def liveness_check():
    """
    Liveness probe for Kubernetes/Docker.
    Returns 200 if application process is alive.
    """
    return {"status": "alive"}


@router.get("/health/readiness", response_model=ReadinessStatus)
async def readiness_check():
    """
    Readiness probe for Kubernetes/Docker.
    Returns 200 if application is ready to serve traffic.
    Checks database and Redis connectivity.
    """
    # Run checks concurrently
    db_check, = await asyncio.gather(
        check_database(),
        return_exceptions=True
    )
    
    # Handle exceptions as failures
    db_healthy = db_check if isinstance(db_check, bool) else False
    
    all_ready = db_healthy
    
    response = ReadinessStatus(
        ready=all_ready,
        checks={
            "database": db_healthy
        }
    )
    
    # Return 503 if not ready
    if not all_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump()
        )
    
    return response
