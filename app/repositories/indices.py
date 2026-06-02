"""
Repository for caching index catalogue entries and index members in MongoDB.

Two collections are used:
  - index_catalogue: one document per index (keyed by ISIN), stores IndexInfo fields.
  - index_members:   one document per index (keyed by ISIN), stores the members list.

Both collections use a TTL controlled by INDEX_CACHE_TTL_DAYS (default: 3 days).
"""

from datetime import UTC, datetime, timedelta

from pymongo.asynchronous.collection import AsyncCollection

from app.core.database import Collections, get_collection
from app.core.logging import logger
from app.core.settings import get_settings
from app.models.indices import IndexInfo, IndexMember


class IndicesRepository:
    """Repository for index catalogue and member caching."""

    def __init__(self) -> None:
        self._catalogue: AsyncCollection | None = None
        self._members: AsyncCollection | None = None

    @property
    def catalogue(self) -> AsyncCollection:
        if self._catalogue is None:
            self._catalogue = get_collection(Collections.INDEX_CATALOGUE)
        return self._catalogue

    @property
    def members(self) -> AsyncCollection:
        if self._members is None:
            self._members = get_collection(Collections.INDEX_MEMBERS)
        return self._members

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ttl(self) -> timedelta:
        return timedelta(days=get_settings().cache.index_cache_ttl_days)

    def _is_fresh(self, cached_at: datetime) -> bool:
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - cached_at < self._ttl()

    # ------------------------------------------------------------------
    # Index catalogue
    # ------------------------------------------------------------------

    async def get_catalogue(self) -> list[IndexInfo] | None:
        """Return all cached IndexInfo entries if the cache is fresh, else None."""
        docs = await self.catalogue.find({}, {"_id": 0, "cached_at": 0}).to_list()
        if not docs:
            return None
        # Cache is stale if the oldest document exceeds TTL
        oldest = min(
            (doc["cached_at"] for doc in await self.catalogue.find({}, {"cached_at": 1}).to_list()),
            default=None,
        )
        if oldest is None or not self._is_fresh(oldest):
            logger.debug("Index catalogue cache is stale or empty")
            return None
        logger.debug("Index catalogue cache hit (%d entries)", len(docs))
        return [IndexInfo(**doc) for doc in docs]

    async def save_catalogue(self, indices: list[IndexInfo]) -> None:
        """Upsert all IndexInfo entries into the catalogue collection."""
        now = datetime.now(UTC)
        for index in indices:
            doc = index.model_dump()
            doc["cached_at"] = now
            await self.catalogue.update_one(
                {"isin": index.isin},
                {"$set": doc},
                upsert=True,
            )
        logger.debug("Index catalogue cached (%d entries)", len(indices))

    # ------------------------------------------------------------------
    # Index members
    # ------------------------------------------------------------------

    async def get_members(self, isin: str) -> list[IndexMember] | None:
        """Return cached members for *isin* if fresh, else None."""
        doc = await self.members.find_one({"isin": isin})
        if not doc:
            return None
        cached_at: datetime = doc.get("cached_at")
        if cached_at is None or not self._is_fresh(cached_at):
            logger.debug("Index members cache stale for ISIN %s", isin)
            return None
        logger.debug("Index members cache hit for ISIN %s (%d members)", isin, len(doc.get("members", [])))
        return [IndexMember(**m) for m in doc["members"]]

    async def save_members(self, isin: str, members: list[IndexMember]) -> None:
        """Upsert the members list for *isin* into the members collection."""
        doc = {
            "isin": isin,
            "members": [m.model_dump() for m in members],
            "cached_at": datetime.now(UTC),
        }
        await self.members.update_one({"isin": isin}, {"$set": doc}, upsert=True)
        logger.debug("Index members cached for ISIN %s (%d members)", isin, len(members))
