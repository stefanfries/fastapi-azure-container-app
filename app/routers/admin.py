"""Administrative endpoints for runtime operations."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from pymongo.errors import PyMongoError

from app.core.logging import logger
from app.core.security import require_api_key
from app.services.log_level_manager import (
    get_runtime_log_level,
    persist_log_level,
    set_runtime_log_level,
)

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_api_key)])


class LogLevelResponse(BaseModel):
    """Response payload for runtime log-level endpoints."""

    log_level: str


class UpdateLogLevelRequest(BaseModel):
    """Request payload for runtime log-level changes."""

    model_config = ConfigDict(extra="forbid")

    log_level: str
    persist: bool = True


@router.get("/log-level", response_model=LogLevelResponse)
async def get_log_level() -> LogLevelResponse:
    """Return current effective runtime log level."""
    return LogLevelResponse(log_level=get_runtime_log_level())


@router.put("/log-level", response_model=LogLevelResponse)
async def update_log_level(payload: UpdateLogLevelRequest) -> LogLevelResponse:
    """Update runtime log level and optionally persist it in MongoDB."""
    try:
        level = set_runtime_log_level(payload.log_level)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.persist:
        try:
            await persist_log_level(level)
        except RuntimeError as exc:
            logger.warning("Could not persist log-level override: database not initialized")
            raise HTTPException(status_code=503, detail="Database is not initialized") from exc
        except PyMongoError as exc:
            logger.warning("Could not persist log-level override: %s", exc)
            raise HTTPException(status_code=503, detail="Could not persist log level") from exc

    return LogLevelResponse(log_level=level)
