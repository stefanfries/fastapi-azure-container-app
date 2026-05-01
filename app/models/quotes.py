"""
Module: quotes
This module defines the data model for financial quotes (current market prices).
Classes:
    Quote: Represents current market price data for a financial instrument.
"""

from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_extra_types.currency_code import Currency

from app.models.types import ISIN, WKN


class Quote(BaseModel):
    """
    Quote model representing current financial market price data.
    Attributes:
        name (str): Name of the financial instrument.
        wkn (WKN): The WKN (Wertpapierkennnummer) of the financial instrument.
        isin (ISIN | None): The ISIN of the financial instrument, if available.
        bid (float): The bid price of the financial instrument.
        ask (float): The ask price of the financial instrument.
        spread_percent (float): The spread percentage, must be greater than or equal to 0.
        currency (Currency): The currency of the financial instrument.
        timestamp (datetime): The timestamp of the quote data.
        trading_venue (str): The trading venue of the financial instrument.
        id_notation (str): The notation ID of the financial instrument.
    """

    name: str
    wkn: WKN
    isin: ISIN | None = None
    bid: float
    ask: float
    spread_percent: float = Field(..., ge=0)
    currency: Currency
    timestamp: datetime
    trading_venue: str
    id_notation: str
