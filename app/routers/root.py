"""
This module defines the welcome router for the FastAPI application.
The root endpoint returns structured application metadata for API discovery.
"""

from fastapi import APIRouter

from app.core.logging import logger
from app.core.settings import settings

router = APIRouter()


@router.get("/", tags=["root"])
async def read_root():
    """Root endpoint — returns application metadata for API discovery."""
    logger.info("Root endpoint called")
    return {
        "application": settings.app.app_name,
        "version": settings.app.app_version,
        "api_version": "v1",
        "data_sources": ["comdirect"],
        "docs": "/docs",
        "health": "/health",
    }
