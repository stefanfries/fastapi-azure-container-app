"""
This module defines the API routes for quote-related operations (current market prices).
Routes:
    /v1/quotes/{instrument_id} (GET): Fetch current quote data by WKN, ISIN, or search term.
Functions:
    get_quote(instrument_id: str, id_notation: str = None) -> Quote:
        Fetch current market quote data for an instrument.
Dependencies:
    fastapi.APIRouter: Used to create the router for the quote routes.
    app.logging_config.logger: Logger instance for logging information.
"""

from fastapi import APIRouter, Query

from app.logging_config import logger
from app.models.quotes import Quote
from app.parsers.quotes import parse_quote

router = APIRouter(prefix="/v1/quotes", tags=["quotes"])


@router.get("/{instrument_id}", response_model=Quote)
async def get_quote(
    instrument_id: str,
    id_notation: str = Query(None),
) -> Quote:
    """
    Fetch current market quote data for instrument_id.
    This could be:
        ISIN (International Securities Identification Number), or
        WKN (German Wertpapierkennnummer) or
        a general search phrase.
    Args:
        instrument_id: Instrument identifier (WKN, ISIN, or search term)
        id_notation: Optional specific trading venue ID notation
    Returns:
        Quote: Current market price data including bid, ask, spread, timestamp
    """
    logger.info(
        "Fetching quote for instrument_id %s and id_notation %s",
        instrument_id,
        id_notation,
    )
    quote = await parse_quote(instrument_id, id_notation)
    logger.info(
        "Retrieved quote for instrument_id %s and id_notation %s:\n %s",
        instrument_id,
        id_notation,
        quote,
    )
    return quote
