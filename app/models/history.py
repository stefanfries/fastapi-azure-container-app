from datetime import datetime
from typing import List

# import pandas as pd
from pydantic import BaseModel, Field
from typing_extensions import Literal

type Interval = Literal["5min", "15min", "30min", "hour", "day", "week", "month"]

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
    interval: Interval
    data: List[HistoryRecord]
