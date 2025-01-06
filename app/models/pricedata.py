from typing import Optional

from DateTime import datetime
from pydantic import BaseModel


class PriceData(BaseModel):
    """
    PriceData represents the price data model for a financial instrument.
    Attributes:
        ask (float): The asking price for the instrument.
        bid (float): The bidding price for the instrument.
        spread (float): The spread between the asking and bidding prices.
        currency (str): The currency in which the prices are quoted.
        timestamp (str): The timestamp when the prices were last updated.
        source (str): The source of the price data.
        notation_id (Optional[str]): The notation ID associated with the price data.
    """

    ask: float
    bid: float
    spread: float
    currency: str
    timestamp: datetime
    venue: str
    notation_id: Optional[str] = None
