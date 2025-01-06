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
from app.models.basedata import BaseData
from app.parsers.basedata import parse_base_data

router = APIRouter(prefix="", tags=["instruments"])


@router.get("/basedata/{instrument_id}", response_model=BaseData)
async def get_instrument_base_data(instrument_id: str) -> BaseData:
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
    base_data = await parse_base_data(instrument_id)
    logger.info(
        "Retrieved instrument data for instrument_id %s: %s", instrument_id, base_data
    )
    return base_data


@router.get("/pricedata/{instrument_id}")
async def get_instrument_price_data(instrument_id: str) -> dict:
    """
    Fetch instrument price data for instrument_id.
    This could be:
        ISIN (International Securities Identification Number), or
        WKN (German Wertpapierkennnummer) or
        a general search phrase.
    """
    return {
        "instrument_id": instrument_id,
        "ask": 100.0,
        "bid": 100.0,
        "spread": 0.01,
        "currency": "EUR",
        "timestamp": "2021-01-01T00:00:00Z",
        "source: ": "LT Societe Generale",
        "notation_id": "1234",
    }
