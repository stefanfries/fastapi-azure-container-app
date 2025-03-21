from datetime import datetime

from fastapi import APIRouter, Query

from app.logging_config import logger
from app.models.history import HistoryData, Interval
from app.parsers.history import parse_history_data

router = APIRouter(prefix="", tags=["instruments"])


@router.get("/history/{instrument_id}", response_model=HistoryData)
async def get_history_data(
    instrument_id: str,
    start: datetime = Query(None),
    end: datetime = Query(None),
    interval: Interval = Query("day"),
    id_notation: str = Query(None),
) -> HistoryData:
    """
    Fetches historical price data for a given instrument.
    Args:
        instrument_id (str): The unique identifier of the instrument.
    Returns:
        HistoryData: The historical price data of the instrument.
    Logs:
        Logs the process of fetching and retrieving the historical data.
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
