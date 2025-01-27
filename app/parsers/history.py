# import re
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin

import httpx
import pandas as pd

from app.core.constants import BASE_URL, HISTORY_PATH
from app.logging_config import logger
from app.models.history import HistoryData, ValidInterval
from app.parsers.basedata import parse_base_data

interval_identifier = {
    "all": "0",
    "5min": "61",
    "15min": "59",
    "30min": "62",
    "1hour": "63",
    "1day": "16",
    "1week": "41",
    "1month": "8",
}


def is_intraday(interval: ValidInterval) -> bool:
    return interval in ["5min", "15min", "30min", "1hour"]


async def parse_history_data(
    instrument_id: str, start, end, interval: ValidInterval
) -> HistoryData:

    logger.info("parse_history_data: %s", instrument_id)
    basedata = await parse_base_data(instrument_id)

    print(f"{start=}")
    print(f"{end=}")
    print(f"{interval=}")
    print()

    if end is None or end > datetime.now():
        end = datetime.now()

    if start is None or start > end:
        start = end - timedelta(days=10)

    if interval is None:
        interval = "1day"

    print(f"{start=}")
    print(f"{end=}")
    print(f"{interval=}")
    print()

    url = urljoin(BASE_URL, HISTORY_PATH)

    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    query_params = {
        "DATETIME_TZ_END_RANGE": int(end.timestamp()),
        "DATETIME_TZ_END_RANGE_FORMATED": end.strftime("%d.%m.%Y"),
        "DATETIME_TZ_START_RANGE": int(start.timestamp()),
        "DATETIME_TZ_START_RANGE_FORMATED": start.strftime("%d.%m.%Y"),
        "ID_NOTATION": basedata.default_id_notation,
        "INTERVALL": interval_identifier.get(interval, "1day"),
        "WITH_EARNINGS": False,
        "OFFSET": 0,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=query_params)
        print(f"redirected url: {response.url}")
        response.raise_for_status()
        csv_data = StringIO(response.text)
        df = pd.read_csv(
            csv_data,
            skiprows=2,
            delimiter=";",
            quotechar='"',
            decimal=",",
            encoding="iso-8859-15",
        )

        if is_intraday(interval):
            df.columns = ["datetime", "time", "open", "high", "low", "close", "volume"]

            # Combine date and time columns into a single datetime column
            df["datetime"] = pd.to_datetime(
                df["datetime"] + " " + df["time"],
                format="%d.%m.%Y %H:%M",
                errors="coerce",
            )

            # Drop the date and time columns
            df.drop(columns=["time"], inplace=True)

        else:
            df.columns = ["datetime", "open", "high", "low", "close", "volume"]

        df["datetime"] = pd.to_datetime(
            df["datetime"], format="%d.%m.%Y", errors="coerce"
        )

        df["volume"] = (
            df["volume"]
            .str.replace(".", "", regex=False)
            .str.replace(",00", "", regex=False)
            .astype(int)
        )

    # Convert the DataFrame to a list of dictionaries
    data = df.to_dict(orient="records")

    # TODO: implement a function to find the trading_venue for a given id_notation in parsers.basedata

    # build a dict of all id_notations
    id_notations_dict = {
        **basedata.id_notations_life_trading,
        **basedata.id_notations_exchange_trading,
    }

    # find the trading_venue for a given id_notation
    # keys = [key for key, val in d.items() if val == tar]
    trading_venues = [
        trading_venue
        for trading_venue, id_notation in id_notations_dict.items()
        if id_notation == basedata.default_id_notation
    ]

    print(f"trading_venue: {trading_venues[0]}")

    return HistoryData(
        wkn=basedata.wkn,
        name=basedata.name,
        id_notation=str(basedata.default_id_notation),
        trading_venue=str(trading_venues[0]),
        currency="USD",
        start=start,
        end=end,
        interval=interval,
        data=data,
    )
