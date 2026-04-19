"""
Depot Repository for managing user depots (portfolios) in MongoDB.
"""

from typing import List, Optional

from pymongo.asynchronous.collection import AsyncCollection

from app.core.database import Collections, get_collection
from app.core.logging import logger
from app.models.depots import Depot


class DepotRepository:
    """Repository for depot CRUD operations."""

    def __init__(self):
        self._collection: Optional[AsyncCollection] = None

    @property
    def collection(self) -> AsyncCollection:
        if self._collection is None:
            self._collection = get_collection(Collections.DEPOTS)
        return self._collection

    async def find_all(self) -> List[Depot]:
        """Return all depots."""
        logger.debug("Fetching all depots")
        cursor = self.collection.find({})
        docs = await cursor.to_list(length=None)
        for doc in docs:
            doc.pop("_id", None)
        return [Depot(**doc) for doc in docs]

    async def find_by_id(self, depot_id: str) -> Optional[Depot]:
        """Find a depot by its string ID."""
        logger.debug("Looking up depot: %s", depot_id)
        doc = await self.collection.find_one({"id": depot_id})
        if doc:
            doc.pop("_id", None)
            return Depot(**doc)
        return None

    async def create(self, depot: Depot) -> Depot:
        """Insert a new depot. Raises ValueError if depot ID already exists."""
        existing = await self.find_by_id(depot.id)
        if existing:
            raise ValueError(f"Depot '{depot.id}' already exists")
        await self.collection.insert_one(depot.model_dump())
        logger.info("Created depot: %s (%s)", depot.name, depot.id)
        return depot

    async def update(self, depot_id: str, updates: dict) -> bool:
        """Update fields on an existing depot. Returns True if a document was modified."""
        result = await self.collection.update_one(
            {"id": depot_id}, {"$set": updates}
        )
        return result.modified_count > 0

    async def delete(self, depot_id: str) -> bool:
        """Delete a depot by ID. Returns True if a document was deleted."""
        result = await self.collection.delete_one({"id": depot_id})
        return result.deleted_count > 0
