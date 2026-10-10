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
        trading_venue (str): The trading venue of the financial instrument.
        id_notation (str): The notation ID of the financial instrument.
        currency (Currency): The currency of the financial instrument.
        bid (float): The bid price of the financial instrument.
        ask (float): The ask price of the financial instrument.
        spread_percent (float): The spread percentage, must be greater than or equal to 0.
        prev_close (float | None): Previous day's closing price (not available for ETF/Fonds/Bond).
        open (float | None): Opening price of the current trading day.
        high (float | None): Intraday high.
        low (float | None): Intraday low.
        timestamp (datetime): The quote timestamp as displayed by comdirect (naive Berlin time).
        timestamp_utc (datetime): The quote timestamp converted to UTC; not the API fetch time.
    """

    name: str
    wkn: WKN
    isin: ISIN | None = None
    trading_venue: str
    id_notation: str
    currency: Currency
    bid: float
    ask: float
    spread_percent: float = Field(..., ge=0)
    prev_close: float | None = Field(None, description="Previous close (Schluss Vortag / Vortag)")
    open: float | None = Field(None, description="Opening price (Eröffnung)")
    high: float | None = Field(None, description="Intraday high (Hoch)")
    low: float | None = Field(None, description="Intraday low (Tief)")
    timestamp: datetime = Field(
        ..., description="Quote timestamp as displayed by comdirect, in naive Europe/Berlin time"
    )
    timestamp_utc: datetime = Field(
        ..., description="Quote timestamp converted to UTC; this is not the API fetch time"
    )
