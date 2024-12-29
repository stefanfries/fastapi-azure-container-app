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
from app.crud.instruments import (
    extract_instrument_type_from_response,
    extract_soup_from_response,
    extract_wkn_and_isin_from_spoup,
    get_page_from_url,
)

# from app.crud.instruments import get_instrument_data_from_web

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
    # base_data = await get_instrument_data_from_web(instrument_id)
    response = await get_page_from_url(instrument_id)
    redirected_url = extract_instrument_type_from_response(response)
    soup = extract_soup_from_response(response)
    wkn, isin = extract_wkn_and_isin_from_spoup(soup)

    base_data = {"WKN": wkn, "ISIN": isin}

    logger.info(
        "Retrieved instrument data for instrument_id %s: %s", instrument_id, base_data
    )

    return {f"{instrument_id}": base_data}
