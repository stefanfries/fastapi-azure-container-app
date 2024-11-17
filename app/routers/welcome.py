"""
Module to define a root endpoint for health check purposes
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["welcome"])
async def read_root():
    """Root endpoint for health check purposes"""

    return {"message": "Welcome, the app is live!"}
