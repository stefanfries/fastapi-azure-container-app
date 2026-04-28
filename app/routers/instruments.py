"""
This module defines the API routes for instrument-related operations.
Routes:
    /v1/instruments (GET): List cached instruments, optionally filtered by asset class.
    /v1/instruments/{instrument_id} (GET): Fetch instrument master data by WKN, ISIN, or search term.
Functions:
    list_instruments(asset_class: AssetClass | None) -> list[Instrument]:
        Return all cached instruments, optionally filtered by asset class.
    get_instrument(instrument_id: str) -> dict:
        Fetch instrument data by identifier.
Dependencies:
    fastapi.APIRouter: Used to create the router for the instrument routes.
    app.logging_config.logger: Logger instance for logging information.
"""

from fastapi import APIRouter, Depends

from app.core.logging import logger
from app.core.security import require_api_key
from app.models.instruments import AssetClass, Instrument
from app.parsers.instruments import parse_instrument_data
from app.repositories.instruments import InstrumentRepository

router = APIRouter(
    prefix="/v1/instruments", tags=["instruments"], dependencies=[Depends(require_api_key)]
)

_repo = InstrumentRepository()


@router.get("/", response_model=list[Instrument])
async def list_instruments(asset_class: AssetClass | None = None) -> list[Instrument]:
    """
    List all cached instruments, optionally filtered by asset class.

    Args:
        asset_class: Optional filter (e.g. Stock, Bond, ETF, Fund, Warrant,
                     Certificate, Commodity, Index, Currency).
    Returns:
        list[Instrument]: Matching instruments sorted by name.
    """
    logger.info("Listing instruments (asset_class=%s)", asset_class)
    return await _repo.find_all(asset_class=asset_class.value if asset_class else None)


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
