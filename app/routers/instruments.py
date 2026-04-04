"""
This module defines the API routes for instrument-related operations.
Routes:
    /v1/instruments/{instrument_id} (GET): Fetch instrument master data by WKN, ISIN, or search term.
Functions:
    get_instrument(instrument_id: str) -> dict:
        Fetch instrument data by identifier.
Dependencies:
    fastapi.APIRouter: Used to create the router for the instrument routes.
    app.logging_config.logger: Logger instance for logging information.
"""

from fastapi import APIRouter

from app.logging_config import logger
from app.models.instruments import Instrument
from app.parsers.instruments import parse_instrument_data

router = APIRouter(prefix="/v1/instruments", tags=["instruments"])


@router.get("/{instrument_id}", response_model=Instrument)
async def get_instrument(instrument_id: str) -> Instrument:
    """
    Fetch instrument master data by an instrument_id.
    This could be:
        ISIN (International Securities Identification Number), or
        WKN (German Wertpapierkennnummer) or
        a general search phrase.
    Args:
        instrument_id (str): The identifier of the instrument to fetch.
    Returns:
        Instrument: An object containing the instrument master data.
    """

    logger.info("Fetching instrument data for instrument_id %s", instrument_id)
    instrument_data = await parse_instrument_data(instrument_id)
    logger.info(
        "Retrieved instrument data for instrument_id %s: %s", instrument_id, instrument_data
    )
    return instrument_data
