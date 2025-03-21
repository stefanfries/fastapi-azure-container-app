from fastapi import APIRouter, Query

from app.logging_config import logger
from app.models.pricedata import PriceData
from app.parsers.pricedata import parse_price_data

router = APIRouter(prefix="", tags=["instruments"])


@router.get("/pricedata/{instrument_id}", response_model=PriceData)
async def get_price_data(
    instrument_id: str,
    id_notation: str = Query(None),
) -> PriceData:
    """
    Fetch instrument price data for instrument_id.
    This could be:
        ISIN (International Securities Identification Number), or
        WKN (German Wertpapierkennnummer) or
        a general search phrase.
    """
    logger.info(
        "Fetching pricedata for instrument_id %s and id_notation %s",
        instrument_id,
        id_notation,
    )
    price_data = await parse_price_data(instrument_id, id_notation)
    logger.info(
        "Retrieved pricedata for instrument_id %s and id_notation %s:\n %s",
        instrument_id,
        id_notation,
        price_data,
    )
    return price_data
