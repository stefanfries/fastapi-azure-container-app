"""This module defines the API routes for handling depot-related operations.
Routes:
    - GET /depots/{depot_id}: Fetches all depots information for a given depot ID.
    - GET /depots/{depot_id}: Fetches instrument data by ISIN (International Securities Identification Number).
    Fetch all depots information for a given depot ID.
        depot_id (str): The ID of the depot to fetch information for.
        dict: A dictionary containing the depot information.
    pass
        depot_id (str): The ID of the depot to fetch information for.
    pass
"""

from fastapi import APIRouter

from app.applogger import logger

router = APIRouter(prefix="/depots", tags=["depots"])


@router.get("/")
async def get_all_depots() -> dict:
    """
    Fetch the list of all depots.
    Args:
        depot_id (str): The ID of the depot.
    Returns:
        dict: A dictionary containing the list of all depots.
    """

    logger.info("Fetching list of all depots")

    logger.info("Retrieved list of all depots")

    return {"List of all depots": "['Depot A', 'Depot B', '...']"}


@router.get("/{depot_id}")
async def get_by_depot_id(depot_id: str) -> dict:
    """
    Fetch instrument data by ISIN (International Securities Identification Number).
    Args:
        isin (str): The ISIN of the instrument to fetch.
    Returns:
        dict: A dictionary containing the instrument data.
    """

    logger.info("Fetching depot infos for depot_id %s", depot_id)

    logger.info(
        "Retrieved depot infos for depot_id %s: Timo´s Depot",
        depot_id,
    )

    return {f"{depot_id}": "Timo´s Depot"}
