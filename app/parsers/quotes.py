"""
Parser for current market quote data.

Scrapes the comdirect instrument detail page to extract the current bid/ask
prices, spread, currency, timestamp, and trading venue for a given instrument.

Functions:
    parse_quote: Fetch and parse the current market quote for an instrument.
"""

import re
from datetime import datetime

from bs4 import BeautifulSoup
from fastapi import HTTPException, status

from app.core.constants import special_asset_classes
from app.core.logging import logger
from app.models.instruments import AssetClass
from app.models.quotes import Quote
from app.parsers.instruments import parse_instrument_data
from app.parsers.plugins.parsing_utils import extract_name_from_h1, extract_wkn_from_h2
from app.parsers.utils import check_valid_id_notation
from app.scrapers.scrape_url import fetch_one


async def parse_quote(instrument_id: str, id_notation: str | None) -> Quote:
    """
    Parses quote data (current market prices) for a given financial instrument.
    Args:
        instrument_id (str): The ID of the financial instrument to fetch and parse data for.
        id_notation (str | None): Optional ID notation for specific trading venue.
    Returns:
        Quote: An object containing parsed quote data including name, WKN, bid price, ask price,
               spread percentage, currency, timestamp, trading venue, and ID notation.
    Raises:
        ValueError: If the response does not contain the expected data.
    """

    logger.debug("parse_quote(%s, id_notation=%s)", instrument_id, id_notation)
    instrument_data = await parse_instrument_data(instrument_id)

    if instrument_data.asset_class not in (AssetClass.STOCK, AssetClass.WARRANT):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Quote data for asset class {instrument_data.asset_class} not implemented",
        )

    match id_notation:
        case None:
            id_notation = instrument_data.default_id_notation
        case "preferred_id_notation_exchange_trading":
            id_notation = instrument_data.preferred_id_notation_exchange_trading
        case "preferred_id_notation_life_trading":
            id_notation = instrument_data.preferred_id_notation_life_trading
        case "default_id_notation":
            id_notation = instrument_data.default_id_notation
        case _:
            check_valid_id_notation(instrument_data, id_notation)

    # fetch instrument data from the web for the given id_notation
    response = await fetch_one(str(instrument_data.wkn), instrument_data.asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")

    # extract currency from soup object
    currency = soup.find_all("meta", itemprop="priceCurrency")[0]["content"]

    # extract name from soup object
    name = extract_name_from_h1(soup, remove_suffix=instrument_data.asset_class.comdirect_label)

    # extract WKN from soup object
    wkn_position = 2 if instrument_data.asset_class in special_asset_classes else 1
    wkn = extract_wkn_from_h2(soup, position_offset=wkn_position)

    # extract Table "Kursdaten" from soup object
    table = soup.find("h2", text=re.compile("Kursdaten")).parent.find("table")

    # Extract Bid Price
    bid_str = (
        table.find("th", text=re.compile("Geld"))
        .find_next("span", class_="realtime-indicator--value")
        .text
    )
    bid = float(bid_str.replace(".", "").replace(",", "."))

    # Extract Ask Price
    ask_str = (
        table.find("th", text=re.compile("Brief"))
        .find_next("span", class_="realtime-indicator--value")
        .text
    )

    ask = float(ask_str.replace(".", "").replace(",", "."))

    # Calculate spread as percentage of ask price (matching comdirect's formula)
    spread_percent = (ask - bid) / ask * 100

    # Extract Timestamp
    timestamp_str = table.find("th", text=re.compile("Zeit")).find_next("td").text

    # Use regular expression to remove unnecessary spaces and newlines
    cleaned_timestamp_str = re.sub(r"\s+", " ", timestamp_str).strip()

    # Convert to datetime object
    timestamp = datetime.strptime(cleaned_timestamp_str, "%d.%m.%y %H:%M")

    trading_venue = table.find("th", string="Börse").find_next("td").text

    quote = Quote(
        name=name,
        wkn=wkn,
        isin=instrument_data.isin,
        bid=bid,
        ask=ask,
        spread_percent=spread_percent,
        currency=currency,
        timestamp=timestamp,
        trading_venue=trading_venue,
        id_notation=id_notation,
    )
    logger.debug("parse_quote(%s) done", instrument_id)
    return quote
