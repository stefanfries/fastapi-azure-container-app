"""
MongoDB database configuration and connection management.

This module provides async database connectivity using PyMongo 4.x native async support.
It manages the connection lifecycle integrated with FastAPI's startup/shutdown events.
"""

from typing import Optional

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.settings import settings
from app.logging_config import logger

# Global database client instance
_client: Optional[MongoClient] = None
_database: Optional[Database] = None


def get_database() -> Database:
    """
    Get the MongoDB database instance.
    
    Returns:
        Database: MongoDB database instance
        
    Raises:
        RuntimeError: If database connection is not initialized
    """
    if _database is None:
        raise RuntimeError(
            "Database connection not initialized. "
            "Call connect_to_database() first during application startup."
        )
    return _database


async def connect_to_database() -> None:
    """
    Establish connection to MongoDB Atlas.
    
    This function should be called during FastAPI application startup.
    
    Raises:
        ValueError: If MONGODB_CONNECTION_STRING is not configured
        ConnectionFailure: If connection to MongoDB fails
    """
    global _client, _database
    
    try:
        logger.info("Connecting to MongoDB Atlas...")
        
        # Create MongoDB client with connection pooling
        _client = MongoClient(
            settings.database.mongodb_connection_string,
            serverSelectionTimeoutMS=settings.database.server_selection_timeout_ms,
            maxPoolSize=settings.database.max_pool_size,
            minPoolSize=settings.database.min_pool_size,
            retryWrites=True,
            w="majority",  # Write concern
        )
        
        # Verify connection by pinging the database
        _client.admin.command("ping")
        
        # Get database instance
        _database = _client[settings.database.db_name]
        
        logger.info("Successfully connected to MongoDB Atlas (database: %s)", settings.database.db_name)
        
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error("Failed to connect to MongoDB: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error connecting to MongoDB: %s", e)
        raise


async def close_database_connection() -> None:
    """
    Close the MongoDB connection.
    
    This function should be called during FastAPI application shutdown.
    """
    global _client, _database
    
    if _client:
        logger.info("Closing MongoDB connection...")
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed")


def get_collection(collection_name: str):
    """
    Get a MongoDB collection from the database.
    
    Args:
        collection_name (str): Name of the collection
        
    Returns:
        Collection: MongoDB collection instance
    """
    db = get_database()
    return db[collection_name]


# Collection names constants
class Collections:
    """MongoDB collection names."""
    USERS = "users"
    DEPOTS = "depots"
    INSTRUMENTS = "instruments"
    QUOTES = "quotes"
    HISTORY = "history"
