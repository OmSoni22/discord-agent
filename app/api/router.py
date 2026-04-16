"""Central API router that aggregates all route modules."""

from fastapi import APIRouter

from app.api.stream_routes import router as stream_router

api_router = APIRouter()

# Agent streaming & session routes
api_router.include_router(stream_router)
