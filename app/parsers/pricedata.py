import re
from datetime import datetime

from bs4 import BeautifulSoup
from fastapi import HTTPException, status

# from app.logging_config import logger
from app.models.basedata import AssetClass
from app.models.pricedata import PriceData
from app.parsers.basedata import parse_base_data, parse_name, parse_wkn
from app.scrapers.scrape_url import fetch_one


def check_id_notation_valid(basedata, id_notation):
    """
    Validates the given id_notation against the basedata.
    This function checks if the provided id_notation is present in either
    the id_notations_life_trading or id_notations_exchange_trading values
    of the basedata. If the id_notation is not found in either, an HTTPException
    is raised with a 400 status code.
    Args:
        basedata: An object containing id_notations_life_trading and id_notations_exchange_trading.
        id_notation: The id_notation to be validated.
    Raises:
        HTTPException: If the id_notation is not valid for the given basedata.
    """

    if (
        id_notation not in basedata.id_notations_life_trading.values()
        and id_notation not in basedata.id_notations_exchange_trading.values()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid id_notation {id_notation} for instrument {basedata.instrument_id}",
        )


async def parse_price_data(instrument_id: str, id_notation: str | None) -> PriceData:
    """
    Parses price data for a given financial instrument.
    Args:
        instrument_id (str): The ID of the financial instrument to fetch and parse data for.
    Returns:
        PriceData: An object containing parsed price data including name, WKN, bid price, ask price, spread percentage, currency, timestamp, trading venue, and ID notation.
    Raises:
        ValueError: If the response does not contain the expected data.
    """

    # as basedata are not known, parse them first
    # TODO: implement basedata fetch from database
    # TODO: implement basedata caching
    basedata = await parse_base_data(instrument_id)

    if basedata.asset_class not in (AssetClass.STOCK, AssetClass.WARRANT):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Pricedata for asset class {basedata.asset_class} not implemented",
        )

    match id_notation:
        case None:
            id_notation = basedata.default_id_notation
        case "preferred_id_notation_exchange_trading":
            id_notation = basedata.preferred_id_notation_exchange_trading
        case "preferred_id_notation_life_trading":
            id_notation = basedata.preferred_id_notation_life_trading
        case "default_id_notation":
            id_notation = basedata.default_id_notation
        case _:
            check_id_notation_valid(basedata, id_notation)

    # fetch instrument data from the web for the given id_notation
    response = await fetch_one(str(basedata.wkn), basedata.asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")

    # extract currency from soup object
    currency = soup.find_all("meta", itemprop="priceCurrency")
    print(f"length: {len(currency)}")

    currency = soup.find_all("meta", itemprop="priceCurrency")[0]["content"]
    print(f"Currency: {currency}")

    # extract name from soup object
    name = parse_name(basedata.asset_class, soup)

    # extract WKN from soup object
    wkn = parse_wkn(basedata.asset_class, soup)

    # extract Table "Kursdaten" from soup object
    table = soup.find("h2", text=re.compile("Kursdaten")).parent.find("table")

    # Extract Bid Price
    bid_str = (
        table.find("th", text=re.compile("Geld"))
        .find_next("span", class_="realtime-indicator--value")
        .text
    )
    bid = float(bid_str.replace(".", "").replace(",", "."))
    print(f"Bid Price: {bid}")

    # Extract Ask Price
    ask_str = (
        table.find("th", text=re.compile("Brief"))
        .find_next("span", class_="realtime-indicator--value")
        .text
    )

    ask = float(ask_str.replace(".", "").replace(",", "."))
    print(f"Ask Price: {ask}")

    spread_percent = (ask - bid) / ((ask + bid) / 2) * 100

    # Extract Timestamp
    timestamp_str = table.find("th", text=re.compile("Zeit")).find_next("td").text

    # Use regular expression to remove unnecessary spaces and newlines
    cleaned_timestamp_str = re.sub(r"\s+", " ", timestamp_str).strip()

    # Convert to datetime object
    timestamp = datetime.strptime(cleaned_timestamp_str, "%d.%m.%y %H:%M")
    print(f"timpstamp: {timestamp}")

    trading_venue = table.find("th", string="Börse").find_next("td").text

    price_data = PriceData(
        name=name,
        wkn=wkn,
        bid=bid,
        ask=ask,
        spread_percent=spread_percent,
        currency=currency,
        timestamp=timestamp,
        trading_venue=trading_venue,
        id_notation=id_notation,
    )
    return price_data
