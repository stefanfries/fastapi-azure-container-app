"""
This module defines the API routes for instrument-related operations.
Routes:
    /instruments/{instrument_id} (GET): Fetch instrument data by ISIN (International Securities Identification Number).
Functions:
    get_by_instrument_id(instrument_id: str) -> dict:
        Fetch instrument data by ISIN.
Dependencies:
    fastapi.APIRouter: Used to create the router for the instrument routes.
    app.applogger.logger: Logger instance for logging information.
"""

from fastapi import APIRouter

from app.applogger import logger

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/{instrument_id}")
async def get_by_instrument_id(instrument_id: str) -> dict:
    """
    Fetch instrument data by ISIN (International Securities Identification Number).
    Args:
        isin (str): The ISIN of the instrument to fetch.
    Returns:
        dict: A dictionary containing the instrument data.
    """

    logger.info("Fetching instrument data for instrument_id %s", instrument_id)

    logger.info(
        "Retrieved instrument data for instrument_id %s: Apple Corporation",
        instrument_id,
    )

    return {f"{instrument_id}": "Apple Corporation"}
