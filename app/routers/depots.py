"""
Router for depot (portfolio) endpoints.

Provides two endpoints:
    GET /depots/        — list all known depots
    GET /depots/{depot_id} — fetch a single depot by its ID

Functions:
    get_all_depots:   Return the list of all depots.
    get_by_depot_id:  Return a single depot identified by *depot_id*.

Dependencies:
    fastapi.APIRouter: Used to create the router for the depot routes.
    app.core.logging.logger: Logger instance for logging information.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter

from app.core.logging import logger
from app.models.depots import Depot

router = APIRouter(prefix="/depots", tags=["depots"])


@router.get("/")
async def get_all_depots() -> List[Depot]:
    """Return the list of all depots.

    Returns:
        list[Depot]: All known depots with their metadata and holdings.
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
    """Return a single depot identified by *depot_id*.

    Args:
        depot_id: The unique identifier of the depot to fetch.

    Returns:
        Depot: The depot with its metadata and holdings.
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
