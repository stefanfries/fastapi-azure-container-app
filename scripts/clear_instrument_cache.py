"""One-off script: delete all cached instrument documents so they are re-fetched."""

import asyncio

from pymongo import AsyncMongoClient

from app.core.settings import get_settings


async def main() -> None:
    settings = get_settings()
    uri = settings.database.mongodb_connection_string.get_secret_value()
    db_name = settings.database.db_name

    client: AsyncMongoClient = AsyncMongoClient(uri)
    try:
        result = await client[db_name]["instruments"].delete_many({})
        print(f"Deleted {result.deleted_count} documents from {db_name}.instruments")
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
