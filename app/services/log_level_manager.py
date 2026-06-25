"""Runtime log-level management with optional MongoDB persistence."""

import logging

from pymongo.errors import PyMongoError

from app.core.database import get_database
from app.core.logging import logger
from app.core.settings import settings

_CONFIG_COLLECTION = "app_config"
_CONFIG_ID = "logging"
_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _normalize_log_level(level: str) -> str:
    """Return normalized uppercase log level or raise ValueError."""
    normalized = level.strip().upper()
    if normalized not in _ALLOWED_LOG_LEVELS:
        raise ValueError(
            f"Unsupported log level '{level}'. Allowed values: {', '.join(sorted(_ALLOWED_LOG_LEVELS))}"
        )
    return normalized


def set_runtime_log_level(level: str) -> str:
    """Set logger level in-memory and return the normalized level."""
    normalized = _normalize_log_level(level)
    logger.setLevel(normalized)
    logger.warning("Runtime log level changed to %s", normalized)
    return normalized


def get_runtime_log_level() -> str:
    """Return the current effective logger level."""
    level = logger.getEffectiveLevel()
    level_name = logging.getLevelName(level)
    return level_name if isinstance(level_name, str) else str(level)


async def load_persisted_log_level() -> str | None:
    """Load log-level override from MongoDB if present and valid."""
    try:
        db = get_database()
    except RuntimeError:
        return None

    try:
        document = await db[_CONFIG_COLLECTION].find_one({"_id": _CONFIG_ID})
    except PyMongoError as exc:
        logger.warning("Could not load persisted log level from MongoDB: %s", exc)
        return None

    if not document:
        return None

    configured_level = document.get("level")
    if not isinstance(configured_level, str):
        logger.warning("Ignoring persisted log level: invalid value type")
        return None

    try:
        return _normalize_log_level(configured_level)
    except ValueError as exc:
        logger.warning("Ignoring persisted log level: %s", exc)
        return None


async def persist_log_level(level: str) -> str:
    """Persist log-level override to MongoDB and return normalized value."""
    normalized = _normalize_log_level(level)
    db = get_database()
    await db[_CONFIG_COLLECTION].update_one(
        {"_id": _CONFIG_ID},
        {
            "$set": {
                "level": normalized,
            }
        },
        upsert=True,
    )
    return normalized


async def initialize_runtime_log_level() -> str:
    """Apply startup log-level from settings and optional MongoDB override."""
    active_level = set_runtime_log_level(settings.app.log_level)
    persisted_level = await load_persisted_log_level()
    if persisted_level and persisted_level != active_level:
        active_level = set_runtime_log_level(persisted_level)
        logger.warning("Applied persisted log-level override from MongoDB: %s", active_level)
    return active_level
