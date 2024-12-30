"""
This module defines the welcome router for the FastAPI application.
It includes a single endpoint that serves as a root endpoint for health check purposes.
The endpoint logs a welcome message and returns a JSON response indicating that the app is live.
"""

from fastapi import APIRouter

from app.logging_config import logger

router = APIRouter()


@router.get("/", tags=["welcome"])
async def read_root():
    """Root endpoint for health check purposes"""
    logger.info("Welcome, the app is live!")
    return {"message": "Welcome, the app is live !"}
