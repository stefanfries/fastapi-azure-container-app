from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin

import httpx
import pandas as pd
from bs4 import BeautifulSoup

from app.core.constants import BASE_URL, HISTORY_PATH
from app.logging_config import logger
from app.models.history import HistoryData, Interval
from app.parsers.basedata import parse_base_data
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
    """
    Parses historical data for a given financial instrument.
    Args:
        instrument_id (str): The ID of the financial instrument.
        start (datetime | None): The start date for the historical data. If None, defaults to 14 days before the end date.
        end (datetime | None): The end date for the historical data. If None or in the future, defaults to the current date.
        interval (Interval): The interval for the historical data (e.g., daily, weekly).
        id_notation (str | None): The notation ID. If None, defaults to the instrument's default notation ID.
    Returns:
        HistoryData: An object containing the parsed historical data, including metadata such as WKN, name, trading venue, currency, and the data itself.
    Raises:
        httpx.HTTPStatusError: If the HTTP request for historical data fails.
    Notes:
        - If the start date is None, greater than the end date, or if the interval is intraday, the start date defaults to 14 days before the end date.
        - The function fetches data in chunks with an offset, concatenates the results, and processes the data into a DataFrame.
        - The DataFrame is then converted to a list of dictionaries for the final output.
        - The function also determines the trading venue and currency for the given notation ID.
    """

    logger.info("parsing basedata for instrument_id: %s", instrument_id)
    basedata = await parse_base_data(instrument_id)

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
            check_valid_id_notation(basedata, id_notation)

    # fetch instrument data from the web for the given id_notation
    response = await fetch_one(str(basedata.wkn), basedata.asset_class, id_notation)
    soup = BeautifulSoup(response.content, "html.parser")

    # extract currency from soup object
    currency = soup.find_all("meta", itemprop="priceCurrency")
    print(f"length: {len(currency)}")
    currency = soup.find_all("meta", itemprop="priceCurrency")[0]["content"]
    print(f"Currency: {currency}")

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

    # TODO: check exact DATETIME_TZ_END_RANGE and DATETIME_TZ_START_RANGE values in comdirect page for different intervals (weeks, months, etc.)

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

    async with httpx.AsyncClient() as client:
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
                decimal=",",
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

        df["datetime"] = pd.to_datetime(
            df["datetime"], format="%d.%m.%Y", errors="coerce"
        )

        df["volume"] = (
            df["volume"]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",00", "", regex=False)
            .astype(int)
        )

    # Convert the DataFrame to a list of dictionaries
    data = df.to_dict(orient="records")

    trading_venue = get_trading_venue(basedata, id_notation)

    return HistoryData(
        wkn=basedata.wkn,
        name=basedata.name,
        id_notation=str(id_notation),
        trading_venue=trading_venue,
        currency=currency,
        start=start,
        end=end,
        interval=interval,
        data=data,  # type: ignore
    )
