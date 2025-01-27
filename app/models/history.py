from datetime import datetime
from typing import List

# import pandas as pd
from pydantic import BaseModel, Field
from typing_extensions import Literal

type ValidInterval = Literal[
    "all", "5min", "15min", "30min", "1hour", "1day", "1week", "1month"
]

type Currency = Literal["EUR", "USD", "CHF"]


class HistoryRecord(BaseModel):
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoryData(BaseModel):
    wkn: str = Field(..., pattern=r"^[A-HJ-NP-Z0-9]{6}$")
    name: str
    id_notation: str
    trading_venue: str
    currency: Currency
    start: datetime
    end: datetime
    interval: ValidInterval
    data: List[HistoryRecord]
