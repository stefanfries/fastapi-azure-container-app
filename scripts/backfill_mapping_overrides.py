"""Backfill known ISIN mapping and constituent-name corrections in MongoDB caches.

This script applies targeted updates to existing cached documents so API callers
get corrected data immediately, without waiting for cache expiration.
"""

import asyncio

from pymongo import AsyncMongoClient

from app.core.settings import get_settings

INSTRUMENT_SYMBOL_OVERRIDES: dict[str, str] = {
    "US74743L1008": "BG",
    "CH0044328745": "CB",
    "CH0114405324": "GRMN",
}

INDEX_MEMBER_NAME_OVERRIDES: dict[str, str] = {
    "US74743L1008": "Bunge Global S.A.",
    "CH0044328745": "Chubb Limited",
    "CH0114405324": "Garmin Ltd.",
}


async def main() -> None:
    settings = get_settings()
    uri = settings.database.mongodb_connection_string.get_secret_value()
    db_name = settings.database.db_name

    client: AsyncMongoClient = AsyncMongoClient(uri)
    try:
        db = client[db_name]
        instruments = db["instruments"]
        index_members = db["index_members"]

        instrument_updates = 0
        for isin, symbol in INSTRUMENT_SYMBOL_OVERRIDES.items():
            result = await instruments.update_many(
                {"isin": isin},
                {
                    "$set": {
                        "global_identifiers.symbol_yfinance": symbol,
                    }
                },
            )
            instrument_updates += result.modified_count

        member_updates = 0
        for isin, name in INDEX_MEMBER_NAME_OVERRIDES.items():
            result = await index_members.update_many(
                {"members.isin": isin},
                {
                    "$set": {
                        "members.$[m].name": name,
                    }
                },
                array_filters=[{"m.isin": isin}],
            )
            member_updates += result.modified_count

        print(
            "Backfill complete: "
            f"instrument_docs_updated={instrument_updates} "
            f"index_member_docs_updated={member_updates}"
        )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
