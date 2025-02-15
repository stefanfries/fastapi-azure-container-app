from datetime import datetime
from typing import List

from pydantic import BaseModel
from typing_extensions import Literal

type Interval = Literal["5min", "15min", "30min", "hour", "day", "week", "month"]

type Currency = Literal["EUR", "USD", "CHF"]


class HistoryRecord(BaseModel):
    """
    HistoryRecord represents a financial record with historical data.
    Attributes:
        datetime (datetime): The date and time of the record.
        open (float): The opening price.
        high (float): The highest price.
        low (float): The lowest price.
        close (float): The closing price.
        volume (int): The trading volume.
    """

    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoryData(BaseModel):
    """
    HistoryData represents the historical data for a financial instrument.
    Attributes:
        wkn (Wkn): The WKN (Wertpapierkennnummer) of the financial instrument.
        name (str): The name of the financial instrument.
        id_notation (str): The notation ID of the financial instrument.
        trading_venue (str): The trading venue where the instrument is traded.
        currency (Currency): The currency in which the instrument is traded.
        start (datetime): The start date of the historical data period.
        end (datetime): The end date of the historical data period.
        interval (Interval): The interval at which the historical data is recorded.
        data (List[HistoryRecord]): A list of historical records for the financial instrument.
    """

    wkn: str
    name: str
    id_notation: str
    trading_venue: str
    currency: Currency
    start: datetime
    end: datetime
    interval: Interval
    data: List[HistoryRecord]
