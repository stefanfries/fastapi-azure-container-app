from fastapi import APIRouter

from app.applogger import logger

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/isin/{isn}")
async def get_by_isin(isin: str) -> dict:
    """
    Fetch instrument data by ISIN (International Securities Identification Number).
    Args:
        isin (str): The ISIN of the instrument to fetch.
    Returns:
        dict: A dictionary containing the instrument data.
    """

    logger.info("Fetching instrument data for ISON %s", isin)
    logger.info("Retrieved instrument data for ISIN %s: Apple Corporation", isin)

    return {f"{isin}": "Apple Corporation"}


@router.get("/wkn/{wkn}")
async def get_by_wkn(wkn: str) -> dict:
    """
    Fetch instrument data by WKN (Wertpapierkennnummer).
    Args:
        wkn (str): The WKN of the instrument to fetch.
    Returns:
        dict: A dictionary containing the instrument data.
    """

    logger.info("Fetching instrument data for WKN %s", wkn)
    logger.info("Retrieved instrument data for WKN %s: Apple Corporation", wkn)

    return {f"{wkn}": "Apple Corporation"}


@router.get("/search/{serach_phrase}")
async def get_by_search_phrase(search_phrase: str) -> dict:
    """
    Fetch instrument data by search phrase.
    Args:
        search_phase (str): The search_phrase used to lookup the instrument to fetch.
    Returns:
        dict: A dictionary containing the instrument data.
    """

    logger.info("Fetching instrument data for search phrase %s", search_phrase)
    logger.info(
        "Retrieved instrument data for search phrase %s: Apple Corporation",
        search_phrase,
    )

    return {f"{search_phrase}": "Apple Corporation"}
