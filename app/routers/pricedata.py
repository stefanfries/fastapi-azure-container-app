from fastapi import APIRouter

from app.logging_config import logger
from app.models.pricedata import PriceData
from app.parsers.pricedata import parse_price_data

router = APIRouter(prefix="", tags=["instruments"])


@router.get("/pricedata/{instrument_id}", response_model=PriceData)
async def get_instrument_price_data(instrument_id: str) -> PriceData:
    """
    Fetch instrument price data for instrument_id.
    This could be:
        ISIN (International Securities Identification Number), or
        WKN (German Wertpapierkennnummer) or
        a general search phrase.
    """
    logger.info("Fetching pricedata for instrument_id %s", instrument_id)
    price_data = await parse_price_data(instrument_id)
    logger.info(
        "Retrieved pricedata for instrument_id %s: %s", instrument_id, price_data
    )
    return price_data
