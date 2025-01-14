import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from fastapi import HTTPException, status

# from app.logging_config import logger
from app.models.basedata import AssetClass
from app.models.pricedata import PriceData
from app.parsers.basedata import parse_asset_class, parse_name, parse_wkn
from app.scrapers.scrape_url import fetch_base_one, fetch_details_one


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

    response = await fetch_base_one(instrument_id)

    # extract ID_NOTATION from query string of redirected URL
    if id_notation is None:
        redirected_url = str(response.url)
        query = urlparse(redirected_url).query
        params = parse_qs(query)
        id_notation = params.get("ID_NOTATION", [None])[0]

    # extract asset class from response
    asset_class = parse_asset_class(response)

    if asset_class not in (AssetClass.STOCK, AssetClass.WARRANT):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Price Data for asset class {asset_class} not implemented",
        )

    response = await fetch_details_one(instrument_id, asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")

    currency = soup.find_all("meta", itemprop="priceCurrency")[0]["content"]
    print(f"Currency: {currency}")

    # extract name from soup object
    name = parse_name(asset_class, soup)
    # extract WKN from soup object
    wkn = parse_wkn(asset_class, soup)

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
