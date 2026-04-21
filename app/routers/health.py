"""
Health check endpoints for liveness and readiness probes.

Designed for Azure Container Apps health probe configuration:
  - Liveness probe:  GET /health        (fast, no dependency checks)
  - Readiness probe: GET /health/ready  (checks database + external access)
"""

from datetime import UTC, datetime

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.database import get_database
from app.core.logging import logger
from app.core.settings import settings

router = APIRouter(tags=["health"])

# robots.txt is always present, lightweight, and stable — ideal for a reachability probe
_COMDIRECT_PROBE_URL = "https://www.comdirect.de/robots.txt"


@router.get("/health", status_code=200)
async def liveness():
    """
    Liveness probe — confirms the application process is running.

    Returns 200 immediately without checking dependencies.
    Should respond in < 100 ms.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness():
    """
    Readiness probe — confirms all critical dependencies are reachable.

    Checks:
    - MongoDB Atlas connection (ping)
    - comdirect.de HTTP reachability

    Returns 200 when all checks pass, 503 when any check fails.
    """
    checks: dict[str, str] = {}
    overall_ok = True

    # --- Database check ---
    try:
        db = get_database()
        await db.command("ping")
        checks["database"] = "healthy"
    except Exception as exc:
        logger.warning("Readiness check — database unhealthy: %s", exc)
        checks["database"] = "unhealthy"
        overall_ok = False

    # --- comdirect reachability check ---
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.head(_COMDIRECT_PROBE_URL)
            if response.status_code < 500:
                checks["comdirect_access"] = "healthy"
            else:
                checks["comdirect_access"] = f"unhealthy (HTTP {response.status_code})"
                overall_ok = False
    except Exception as exc:
        logger.warning("Readiness check — comdirect unreachable: %s", exc)
        checks["comdirect_access"] = "unhealthy"
        overall_ok = False

    status_code = 200 if overall_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if overall_ok else "not ready",
            "version": settings.app.app_version,
            "checks": checks,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
