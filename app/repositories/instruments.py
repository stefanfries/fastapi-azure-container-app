"""
Instrument Repository for managing financial instrument master data.

This repository handles CRUD operations and caching for instrument data
including WKN, ISIN, name, asset class, and trading venue notations.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection

from app.core.database import Collections, get_collection
from app.core.logging import logger
from app.core.settings import get_settings
from app.models.instruments import Instrument


def _dates_to_datetime(obj: Any) -> Any:
    """Recursively convert ``datetime.date`` → ``datetime.datetime`` (midnight UTC).

    BSON can encode ``datetime.datetime`` but not bare ``datetime.date``.
    ``datetime`` is a subclass of ``date``, so the isinstance check is ordered.
    """
    if isinstance(obj, datetime):
        return obj
    if isinstance(obj, date):
        return datetime(obj.year, obj.month, obj.day, tzinfo=UTC)
    if isinstance(obj, dict):
        return {k: _dates_to_datetime(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_dates_to_datetime(v) for v in obj]
    return obj


class InstrumentRepository:
    """Repository for instrument master data operations."""

    def __init__(self):
        """Initialize the instrument repository."""
        self._collection: AsyncCollection | None = None

    @property
    def collection(self) -> AsyncCollection:
        """
        Get the instruments collection.

        Returns:
            Collection: MongoDB collection for instruments
        """
        if self._collection is None:
            self._collection = get_collection(Collections.INSTRUMENTS)
        return self._collection

    async def find_by_wkn(self, wkn: str) -> Instrument | None:
        """Find an instrument by WKN. Returns ``None`` if not in the cache."""
        logger.debug("Searching for instrument with WKN: %s", wkn)
        doc = await self.collection.find_one({"wkn": wkn})

        if doc:
            logger.debug("Found instrument in cache: %s", wkn)
            # Remove MongoDB's _id field before creating Pydantic model
            doc.pop("_id", None)
            doc.pop("cached_at", None)
            return Instrument(**doc)

        logger.debug("Instrument not found in cache: %s", wkn)
        return None

    async def find_by_isin(self, isin: str) -> Instrument | None:
        """Find an instrument by ISIN. Returns ``None`` if not in the cache."""
        logger.debug("Searching for instrument with ISIN: %s", isin)
        doc = await self.collection.find_one({"isin": isin})

        if doc:
            logger.debug("Found instrument in cache: %s", isin)
            doc.pop("_id", None)
            doc.pop("cached_at", None)
            return Instrument(**doc)

        logger.debug("Instrument not found in cache: %s", isin)
        return None

    async def save(self, instrument: Instrument) -> None:
        """Upsert an instrument document into the cache collection."""
        # Convert Pydantic model to dict; convert date → datetime for BSON compatibility
        doc = _dates_to_datetime(instrument.model_dump())

        # Add caching metadata
        doc["cached_at"] = datetime.now(UTC)

        # Use WKN as upsert key; fall back to ISIN for foreign instruments without a WKN
        if instrument.wkn is not None:
            filter_key = {"wkn": instrument.wkn}
            log_key = instrument.wkn
        elif instrument.isin is not None:
            filter_key = {"isin": instrument.isin}
            log_key = instrument.isin
        else:
            logger.warning(
                "Cannot save instrument '%s': both WKN and ISIN are None", instrument.name
            )
            return

        logger.info("Saving instrument to cache: %s (%s)", instrument.name, log_key)
        await self.collection.update_one(filter_key, {"$set": doc}, upsert=True)
        logger.debug("Instrument cached successfully: %s", log_key)

    async def is_cache_valid(self, wkn: str) -> bool:
        """Return ``True`` if the cached document for *wkn* is within the TTL.

        TTL is read from settings (``INSTRUMENT_CACHE_TTL_DAYS``, default 7).
        """
        doc = await self.collection.find_one({"wkn": wkn}, {"cached_at": 1})

        if not doc or "cached_at" not in doc:
            return False

        max_age_days = get_settings().cache.instrument_cache_ttl_days
        cached_at = doc["cached_at"]
        # MongoDB returns naive UTC datetimes; make explicit before subtracting.
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=UTC)
        age = datetime.now(UTC) - cached_at

        is_valid = age < timedelta(days=max_age_days)
        logger.debug("Cache validity for %s: %s (age: %s days, ttl: %s days)", wkn, is_valid, age.days, max_age_days)

        return is_valid

    async def delete_by_wkn(self, wkn: str) -> bool:
        """Delete an instrument by WKN. Returns ``True`` if a document was removed."""
        result = await self.collection.delete_one({"wkn": wkn})
        deleted = result.deleted_count > 0

        if deleted:
            logger.info("Deleted instrument from cache: %s", wkn)
        else:
            logger.debug("Instrument not found for deletion: %s", wkn)

        return deleted

    async def find_all(self, asset_class: str | None = None) -> list[Instrument]:
        """
        List all instruments, optionally filtered by asset class.

        Args:
            asset_class: Optional asset class value to filter on (e.g. "Stock", "ETF").

        Returns:
            list[Instrument]: Matching instruments, sorted by name.
        """
        query: dict = {}
        if asset_class is not None:
            query["asset_class"] = asset_class

        logger.debug("Listing instruments with filter: %s", query or "none")
        cursor = self.collection.find(query, {"_id": 0, "cached_at": 0}).sort("name", 1)
        docs = await cursor.to_list()

        return [Instrument(**doc) for doc in docs]

    async def count(self, asset_class: str | None = None) -> int:
        """
        Get the total number of cached instruments, optionally filtered by asset class.

        Args:
            asset_class: Optional asset class value to filter on.

        Returns:
            int: Number of matching instruments in cache.
        """
        query: dict = {}
        if asset_class is not None:
            query["asset_class"] = asset_class
        return await self.collection.count_documents(query)
