"""
Router for historical price data endpoints.

Provides one endpoint:
    GET /v1/history/{instrument_id} — fetch OHLCV price history for an instrument
                                      over a configurable date range and interval.

Functions:
    get_history_data: Return historical price data for the given instrument.

Dependencies:
    fastapi.APIRouter: Used to create the router for the history routes.
    app.core.logging.logger: Logger instance for logging information.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.logging import logger
from app.core.security import require_api_key
from app.models.history import HistoryData, Interval
from app.parsers.history import parse_history_data

router = APIRouter(prefix="/v1/history", tags=["history"], dependencies=[Depends(require_api_key)])


@router.get("/{instrument_id}", response_model=HistoryData)
async def get_history_data(
    instrument_id: str,
    start: datetime = Query(None),
    end: datetime = Query(None),
    interval: Interval = Query("day"),
    id_notation: str = Query(None),
) -> HistoryData:
    """Return historical price data for the given instrument.

    Args:
        instrument_id: Instrument identifier — ISIN, WKN, or a search term.
        start:         Start of the requested date range (inclusive).
                       Defaults to ``None`` (parser applies its own default).
        end:           End of the requested date range (inclusive).
                       Defaults to ``None`` (parser applies its own default).
        interval:      Aggregation interval for OHLCV bars, e.g. ``day``,
                       ``week``, ``month``.  Defaults to ``day``.
        id_notation:   Optional specific trading-venue ID notation used to
                       disambiguate when the same instrument trades on
                       multiple exchanges.

    Returns:
        HistoryData: OHLCV price history for the requested instrument and range.
    """

    logger.info("Fetching history data for instrument_id %s", instrument_id)

    history_data = await parse_history_data(
        instrument_id=instrument_id,
        start=start,
        end=end,
        interval=interval,
        id_notation=id_notation,
    )
    logger.info(
        "successfully retrieved history data for instrument_id %s", instrument_id
    )
    return history_data
