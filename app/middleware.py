"""
This module contains middleware for the FastAPI application.
Middleware:
    log_client_ip_middleware: Logs the client's IP address for each API request.
"""

from fastapi import Request

from app.logging_config import logger


async def log_client_ip_middleware(request: Request, call_next):
    """
    Middleware that logs the client's IP address.
    """
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    logger.info("API called by client IP address: %s", client_ip)
    response = await call_next(request)
    return response
