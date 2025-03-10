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

from datetime import datetime
from typing import List

from fastapi import APIRouter

from app.logging_config import logger
from app.models.depots import Depot

router = APIRouter(prefix="/depots", tags=["depots"])


@router.get("/")
async def get_all_depots() -> List[Depot]:
    """
    Fetch the list of all depots.
    Args:
        depot_id (str): The ID of the depot.
    Returns:
        dict: A dictionary containing the list of all depots.
    """

    logger.info("Fetching list of all depots")

    logger.info("Retrieved list of all depots")

    depot1 = Depot(
        id="1",
        name="Depot MegaTrendFolger",
        items=[],
        cash=1000.0,
        created_at=datetime(2018, 1, 1, 18, 0, 0),
        changed_at=datetime(2021, 7, 7, 18, 0, 0),
    )
    depot2 = Depot(
        id="1",
        name="Depot Stefan",
        items=[],
        cash=1000.0,
        created_at=datetime(2022, 8, 28, 18, 0, 0),
        changed_at=datetime(2025, 2, 28, 18, 0, 0),
    )

    return [depot1, depot2]


@router.get("/{depot_id}")
async def get_by_depot_id(depot_id: str) -> Depot:
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
    depot = Depot(
        id="1",
        name="MegaTrendFolger Depot",
        items=[],
        cash=1000.0,
        created_at=datetime(2021, 7, 7, 18, 0, 0),
        changed_at=datetime(2021, 7, 7, 18, 0, 0),
    )
    return depot
