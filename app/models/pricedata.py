from datetime import datetime

from pydantic import BaseModel, Field


class PriceData(BaseModel):
    """
    PriceData model representing financial price data.
    Attributes:
        wkn (str): The WKN (Wertpapierkennnummer) of the financial instrument, must be a 6-character alphanumeric string.
        bid (float): The bid price of the financial instrument.
        ask (float): The ask price of the financial instrument.
        spread_percent (float): The spread percentage, must be greater than or equal to 0.
        currency (str): The currency of the financial instrument, must be one of 'EUR', 'USD', or 'CHF'.
        timestamp (datetime): The timestamp of the price data.
        venue (str): The trading venue of the financial instrument.
        id_notation (str): The notation ID of the financial instrument.
    """

    name: str
    wkn: str = Field(..., pattern=r"^[A-HJ-NPR-Z0-9]{6}$")
    bid: float
    ask: float
    spread_percent: float = Field(..., ge=0)
    currency: str = Field(..., pattern=r"^EUR|USD|CHF$")
    timestamp: datetime
    trading_venue: str
    id_notation: str
