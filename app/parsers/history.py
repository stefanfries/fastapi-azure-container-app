"""
Parser for historical OHLCV price data.

Scrapes comdirect's CSV export endpoint to return structured historical price
records for a given instrument, date range, and aggregation interval.

Functions:
    is_intraday:        Check whether an interval value is an intraday interval.
    parse_history_data: Fetch and parse OHLCV history for an instrument.
"""

from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from app.core.constants import BASE_URL, HISTORY_PATH
from app.core.logging import logger
from app.models.history import HistoryData, Interval
from app.parsers.instruments import parse_instrument_data
from app.parsers.utils import check_valid_id_notation, get_trading_venue
from app.scrapers.scrape_url import fetch_one

interval_identifier = {
    # "all": "0",
    "5min": "61",
    "15min": "59",
    "30min": "62",
    "hour": "63",
    "day": "16",
    "week": "41",
    "month": "8",
}


def is_intraday(interval: Interval) -> bool:
    """
    Check if the given interval is an intraday interval.
    Args:
        interval (Interval): The interval to check.
    Returns:
        bool: True if the interval is one of "5min", "15min", "30min", or "hour", indicating it is an intraday interval; False otherwise.
    """

    return interval in ["5min", "15min", "30min", "hour"]


async def parse_history_data(
    instrument_id: str,
    start: datetime | None,
    end: datetime | None,
    interval: Interval,
    id_notation: str | None,
) -> HistoryData:
    """Fetch and parse OHLCV history for an instrument.

    Args:
        instrument_id: Instrument identifier (WKN, ISIN, or search term).
        start: Start date; defaults to 14 days before end when ``None`` or for intraday intervals.
        end: End date; defaults to today when ``None`` or in the future.
        interval: Aggregation interval (e.g. ``day``, ``week``, ``month``).
        id_notation: Trading venue notation; defaults to the instrument's default when ``None``.

    Returns:
        HistoryData with WKN, name, trading venue, currency, and OHLCV records.

    Raises:
        httpx.HTTPStatusError: If the HTTP request for historical data fails.
    """

    logger.debug("parse_history_data(%s, interval=%s)", instrument_id, interval)
    instrument_data = await parse_instrument_data(instrument_id)

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

    if end is None or end > datetime.now():
        end = datetime.now()
    if start is None or start > end:
        start = end - timedelta(days=28)
    if (end - start).days < 1:
        start = end - timedelta(days=1)  # ensure at least one day of data
    if is_intraday(interval):
        start = max(
            start, end - timedelta(days=14)
        )  # intraday data is only available for the last 14 days
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    url = urljoin(BASE_URL, HISTORY_PATH)

    query_params = {
        "DATETIME_TZ_END_RANGE": int(end.timestamp()),
        "DATETIME_TZ_END_RANGE_FORMATED": end.strftime("%d.%m.%Y"),
        "DATETIME_TZ_START_RANGE": int(start.timestamp()),
        "DATETIME_TZ_START_RANGE_FORMATED": start.strftime("%d.%m.%Y"),
        "ID_NOTATION": id_notation,
        "INTERVALL": interval_identifier.get(interval, "16"),
        "WITH_EARNINGS": False,
        "OFFSET": 0,
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        df_list = []
        offset = 0

        while offset <= 50:
            query_params.update({"OFFSET": offset})
            try:
                response = await client.get(url, params=query_params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error("HTTP status error: %s", e)
                break
            csv_data = StringIO(response.text)
            df = pd.read_csv(
                csv_data,
                skiprows=2,
                delimiter=";",
                quotechar='"',
                encoding="iso-8859-15",
            )
            df_list.append(df)
            offset += 1

        if df_list:
            df = pd.concat(df_list, ignore_index=True)
        else:
            df = pd.DataFrame()

        if is_intraday(interval):
            df.columns = ["date", "time", "open", "high", "low", "close", "volume"]

            # Combine date and time columns into a single datetime column
            df["datetime"] = pd.to_datetime(
                df["date"] + " " + df["time"],
                format="%d.%m.%Y %H:%M",
                errors="coerce",
            )

            # Drop the date and time column
            df.drop(columns=["date", "time"], inplace=True)

            # make the datetime column the first column
            df = df[["datetime", "open", "high", "low", "close", "volume"]]

        else:
            df.columns = ["datetime", "open", "high", "low", "close", "volume"]

        df["datetime"] = pd.to_datetime(df["datetime"], format="%d.%m.%Y", errors="coerce")
        # Convert German number format to float for open, high, low, and close columns
        for col in ["open", "high", "low", "close"]:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .astype(float)
            )

        df["volume"] = (
            df["volume"]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",00", "", regex=False)
            .astype(int)
        )

    # Sort by datetime in ascending order (oldest first)
    df.sort_values(by="datetime", ascending=True, inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Convert the DataFrame to a list of dictionaries
    data = df.to_dict(orient="records")

    trading_venue = get_trading_venue(instrument_data, id_notation)

    result = HistoryData(
        name=instrument_data.name,
        wkn=instrument_data.wkn,
        isin=instrument_data.isin,
        id_notation=str(id_notation),
        trading_venue=trading_venue,
        currency=currency,
        start=start,
        end=end,
        interval=interval,
        data=data,  # type: ignore
    )
    logger.debug("parse_history_data(%s) done", instrument_id)
    return result
