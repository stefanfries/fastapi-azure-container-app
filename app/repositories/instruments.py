"""
Instrument Repository for managing financial instrument master data.

This repository handles CRUD operations and caching for instrument data
including WKN, ISIN, name, asset class, and trading venue notations.
"""

from datetime import datetime, timedelta
from typing import Optional

from pymongo.collection import Collection

from app.core.database import Collections, get_collection
from app.logging_config import logger
from app.models.instruments import Instrument


class InstrumentRepository:
    """Repository for instrument master data operations."""
    
    def __init__(self):
        """Initialize the instrument repository."""
        self._collection: Optional[Collection] = None
    
    @property
    def collection(self) -> Collection:
        """
        Get the instruments collection.
        
        Returns:
            Collection: MongoDB collection for instruments
        """
        if self._collection is None:
            self._collection = get_collection(Collections.INSTRUMENTS)
        return self._collection
    
    async def find_by_wkn(self, wkn: str) -> Optional[Instrument]:
        """
        Find instrument by WKN (German securities identification number).
        
        Args:
            wkn (str): The WKN to search for
            
        Returns:
            Optional[Instrument]: Instrument if found, None otherwise
        """
        logger.debug("Searching for instrument with WKN: %s", wkn)
        doc = self.collection.find_one({"wkn": wkn})
        
        if doc:
            logger.debug("Found instrument in cache: %s", wkn)
            # Remove MongoDB's _id field before creating Pydantic model
            doc.pop("_id", None)
            doc.pop("cached_at", None)
            return Instrument(**doc)
        
        logger.debug("Instrument not found in cache: %s", wkn)
        return None
    
    async def find_by_isin(self, isin: str) -> Optional[Instrument]:
        """
        Find instrument by ISIN (International Securities Identification Number).
        
        Args:
            isin (str): The ISIN to search for
            
        Returns:
            Optional[Instrument]: Instrument if found, None otherwise
        """
        logger.debug("Searching for instrument with ISIN: %s", isin)
        doc = self.collection.find_one({"isin": isin})
        
        if doc:
            logger.debug("Found instrument in cache: %s", isin)
            doc.pop("_id", None)
            doc.pop("cached_at", None)
            return Instrument(**doc)
        
        logger.debug("Instrument not found in cache: %s", isin)
        return None
    
    async def save(self, instrument: Instrument) -> None:
        """
        Save or update an instrument in the database.
        
        Args:
            instrument (Instrument): The instrument to save
        """
        logger.info("Saving instrument to cache: %s (%s)", instrument.name, instrument.wkn)
        
        # Convert Pydantic model to dict
        doc = instrument.model_dump()
        
        # Add caching metadata
        doc["cached_at"] = datetime.utcnow()
        
        # Upsert based on WKN (unique identifier)
        self.collection.update_one(
            {"wkn": instrument.wkn},
            {"$set": doc},
            upsert=True
        )
        
        logger.debug("Instrument cached successfully: %s", instrument.wkn)
    
    async def is_cache_valid(self, wkn: str, max_age_days: int = 7) -> bool:
        """
        Check if cached instrument data is still valid.
        
        Args:
            wkn (str): The WKN to check
            max_age_days (int): Maximum age in days for cache validity (default: 7)
            
        Returns:
            bool: True if cache is valid, False otherwise
        """
        doc = self.collection.find_one(
            {"wkn": wkn},
            {"cached_at": 1}
        )
        
        if not doc or "cached_at" not in doc:
            return False
        
        cached_at = doc["cached_at"]
        age = datetime.utcnow() - cached_at
        
        is_valid = age < timedelta(days=max_age_days)
        logger.debug(
            "Cache validity for %s: %s (age: %s days)",
            wkn,
            is_valid,
            age.days
        )
        
        return is_valid
    
    async def delete_by_wkn(self, wkn: str) -> bool:
        """
        Delete an instrument by WKN.
        
        Args:
            wkn (str): The WKN of the instrument to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        result = self.collection.delete_one({"wkn": wkn})
        deleted = result.deleted_count > 0
        
        if deleted:
            logger.info("Deleted instrument from cache: %s", wkn)
        else:
            logger.debug("Instrument not found for deletion: %s", wkn)
        
        return deleted
    
    async def count(self) -> int:
        """
        Get the total number of cached instruments.
        
        Returns:
            int: Number of instruments in cache
        """
        return self.collection.count_documents({})
