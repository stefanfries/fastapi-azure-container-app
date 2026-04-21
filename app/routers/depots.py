"""
Router for depot (portfolio) endpoints.

Provides endpoints for listing and retrieving depot data from MongoDB.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.logging import logger
from app.core.security import require_api_key
from app.models.depots import Depot
from app.repositories.depots import DepotRepository

router = APIRouter(prefix="/v1/depots", tags=["depots"], dependencies=[Depends(require_api_key)])

_repo = DepotRepository()


@router.get("/", response_model=list[Depot])
async def get_all_depots() -> list[Depot]:
    """Return all depots from the database."""
    logger.info("Fetching all depots")
    return await _repo.find_all()


@router.get("/{depot_id}", response_model=Depot)
async def get_by_depot_id(depot_id: str) -> Depot:
    """Return a single depot by its ID."""
    logger.info("Fetching depot: %s", depot_id)
    depot = await _repo.find_by_id(depot_id)
    if depot is None:
        raise HTTPException(status_code=404, detail=f"Depot '{depot_id}' not found")
    return depot
