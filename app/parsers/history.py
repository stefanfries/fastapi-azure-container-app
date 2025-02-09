# import re
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import urljoin

import httpx
import pandas as pd

from app.core.constants import BASE_URL, HISTORY_PATH
from app.logging_config import logger
from app.models.history import HistoryData, Interval
from app.parsers.basedata import parse_base_data

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
    return interval in ["5min", "15min", "30min", "hour"]


async def parse_history_data(
    instrument_id: str, start, end, interval: Interval
) -> HistoryData:

    logger.info("parse_history_data: %s", instrument_id)
    basedata = await parse_base_data(instrument_id)

    if interval is None:
        interval = "day"

    if end is None or end > datetime.now():
        end = datetime.now()

    if start is None or start > end or is_intraday(interval):
        start = end - timedelta(days=14)

    url = urljoin(BASE_URL, HISTORY_PATH)

    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)

    # TODO: check exact DATETIME_TZ_END_RANGE and DATETIME_TZ_START_RANGE values in comdirect page for different intervals (weeks, months, etc.)

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
        df_list = []
        offset = 0

        while offset <= 50:
            query_params.update({"OFFSET": offset})
            try:
                response = await client.get(url, params=query_params)
                response.raise_for_status()
                print(f"redirected url: {response.url}")
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
            # if df.empty:
            #     break
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

    # TODO: implement a function to find the currency for a given id_notation in parsers.basedata

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
