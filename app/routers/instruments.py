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

from app.logging_config import logger
from app.models.instruments import InstrumentBaseData
from app.scrapers.instruments import scrape_instrument_base_data

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/{instrument_id}", response_model=InstrumentBaseData)
async def get_instrument_base_data(instrument_id: str) -> InstrumentBaseData:
    """
    Fetch instrument data by an instrument_id.
    This could be:
        ISIN (International Securities Identification Number), or
        WKN (German Wertpapierkennnummer) or
        a general search phrase.
    Args:
        instrument_id (str): The identifier of the instrument to fetch.
    Returns:
        dict: A dictionary containing the instrument data.
    """

    logger.info("Fetching instrument data for instrument_id %s", instrument_id)
    base_data = await scrape_instrument_base_data(instrument_id)
    logger.info(
        "Retrieved instrument data for instrument_id %s: %s", instrument_id, base_data
    )
    return base_data
