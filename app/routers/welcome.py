"""
Module to define a root endpoint for health check purposes
"""

from fastapi import APIRouter

from app.applogger import logger

router = APIRouter()


@router.get("/", tags=["welcome"])
async def read_root():
    """Root endpoint for health check purposes"""
    logger.info("Welcome, the app is up and running!")
    return {"message": "Welcome, the app is up and running!"}
