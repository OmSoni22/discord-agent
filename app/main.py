"""Agentic AI System — FastAPI application entrypoint."""

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.bootstrap import create_components, shutdown_components
from app.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    logger.info("Starting %s...", settings.app_name)

    # Initialize all components (DB + agent stack) and attach to app.state
    components = await create_components()
    for name, component in components.items():
        setattr(app.state, name, component)

    logger.info("%s is ready", settings.app_name)
    logger.info("Tools: %s", [t.name for t in components["tool_registry"].get_all()])
    logger.info("Database: connected (PostgreSQL)")

    try:
        yield
    finally:
        logger.info("Shutting down %s...", settings.app_name)
        await shutdown_components()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Production-grade Agentic AI System with ReAct loop, tool calling, SSE streaming, and persistent threads",
    version="1.0.0",
    debug=settings.debug,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "description": "Agentic AI System with persistent threads, ReAct loop, and SSE streaming",
        "docs": "/api/docs",
        "threads": "/api/v1/threads",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
