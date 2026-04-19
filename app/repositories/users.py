"""
User Repository for managing application users in MongoDB.
"""

from typing import Optional

from pymongo.asynchronous.collection import AsyncCollection

from app.core.database import Collections, get_collection
from app.core.logging import logger
from app.models.users import UserBase, UserStoreDB


class UserRepository:
    """Repository for user CRUD operations."""

    def __init__(self):
        self._collection: Optional[AsyncCollection] = None

    @property
    def collection(self) -> AsyncCollection:
        if self._collection is None:
            self._collection = get_collection(Collections.USERS)
        return self._collection

    async def find_by_username(self, username: str) -> Optional[UserStoreDB]:
        """Find a user by username."""
        logger.debug("Looking up user: %s", username)
        doc = await self.collection.find_one({"username": username})
        if doc:
            doc.pop("_id", None)
            return UserStoreDB(**doc)
        return None

    async def find_by_email(self, email: str) -> Optional[UserStoreDB]:
        """Find a user by email address."""
        logger.debug("Looking up user by email: %s", email)
        doc = await self.collection.find_one({"email": email})
        if doc:
            doc.pop("_id", None)
            return UserStoreDB(**doc)
        return None

    async def create(self, user: UserStoreDB) -> UserStoreDB:
        """Insert a new user. Raises ValueError if username already exists."""
        existing = await self.find_by_username(user.username)
        if existing:
            raise ValueError(f"User '{user.username}' already exists")
        await self.collection.insert_one(user.model_dump())
        logger.info("Created user: %s", user.username)
        return user

    async def update(self, username: str, updates: dict) -> bool:
        """Update fields on an existing user. Returns True if a document was modified."""
        result = await self.collection.update_one(
            {"username": username}, {"$set": updates}
        )
        return result.modified_count > 0

    async def delete(self, username: str) -> bool:
        """Delete a user by username. Returns True if a document was deleted."""
        result = await self.collection.delete_one({"username": username})
        return result.deleted_count > 0
