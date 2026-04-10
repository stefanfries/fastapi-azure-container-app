"""
Pydantic models for the warrant (Optionsschein) finder and detail endpoints.

Classes:
    WarrantPreselection:    Enum for Call/Put/Other/All pre-selection filter.
    WarrantMaturityRange:   Enum for predefined relative maturity date range codes.
    Warrant:                Model for a single warrant result row from the finder table.
    WarrantFinderResponse:  Top-level response envelope for GET /v1/warrants.
    WarrantMarketData:      Live price/quote fields from the Kursdaten section.
    WarrantAnalytics:       Greeks and derived metrics from the Kennzahlen section.
    WarrantReferenceData:   Static instrument attributes from the Stammdaten section.
    WarrantDetailResponse:  Top-level response envelope for GET /v1/warrants/{identifier}.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WarrantPreselection(str, Enum):
    """Pre-selection filter for the warrant type."""

    CALL = "CALL"
    PUT = "PUT"
    OTHER = "OTHER"
    ALL = "ALL"


class WarrantMaturityRange(str, Enum):
    """Predefined relative maturity date range codes accepted by the comdirect finder."""

    NOW = "Range_NOW"
    TWO_WEEKS = "Range_2W"
    ONE_MONTH = "Range_1M"
    THREE_MONTHS = "Range_3M"
    SIX_MONTHS = "Range_6M"
    ONE_YEAR = "Range_1Y"
    TWO_YEARS = "Range_2Y"
    THREE_YEARS = "Range_3Y"
    FIVE_YEARS = "Range_5Y"
    SEVEN_YEARS = "Range_7Y"
    ENDLESS = "Range_ENDLESS"


class Warrant(BaseModel):
    """A single warrant result row from the comdirect Optionsschein Finder.

    Attributes:
        isin:             International Securities Identification Number.
        wkn:              German Wertpapierkennnummer (6 characters).
        link:             Full URL to the warrant detail page on comdirect.
        strike:           Strike price of the warrant, or ``None`` if not available.
        strike_currency:  Currency of the strike price (e.g. ``"USD"``), or ``None``.
        ratio:            Contract ratio (Bezugsverhältnis) as a string (e.g. ``"10 : 1"``), or ``None`` if not available.
        maturity_date:    Expiry / maturity date, or ``None`` if not available.
        last_trading_day: Last day the warrant can be traded, or ``None`` if not available.
        issuer:           Name of the issuing bank or financial institution, or ``None``.
    """

    isin: str = Field(..., description="ISIN")
    wkn: str = Field(..., description="WKN (6-character German securities number)")
    link: str = Field(..., description="URL to the comdirect warrant detail page")
    strike: Optional[float] = Field(None, description="Strike price")
    strike_currency: Optional[str] = Field(None, description="Currency of the strike price")
    ratio: Optional[str] = Field(None, description="Contract ratio (Bezugsverhältnis), e.g. '10 : 1'")
    maturity_date: Optional[date] = Field(None, description="Maturity / expiry date")
    last_trading_day: Optional[date] = Field(None, description="Last trading day")
    issuer: Optional[str] = Field(None, description="Name of the issuer")


class WarrantFinderResponse(BaseModel):
    """
    Response envelope for the GET /v1/warrants endpoint.

    Attributes:
        url:     The comdirect finder URL that was called (useful for verification).
        count:   Number of warrant results returned.
        results: List of warrant results.
    """

    url: str = Field(..., description="Constructed comdirect finder URL")
    count: int = Field(..., description="Number of results returned")
    results: list[Warrant] = Field(default_factory=list, description="Warrant results")


class WarrantMarketData(BaseModel):
    """Live price and quote data (Kursdaten) for a warrant."""

    venue: Optional[str] = Field(None, description="Trading venue name")
    bid: Optional[float] = Field(None, description="Bid (Geld) price")
    ask: Optional[float] = Field(None, description="Ask (Brief) price")
    timestamp: Optional[datetime] = Field(None, description="Quote timestamp")
    spread_percent: Optional[float] = Field(None, description="Bid-ask spread as % of ask")
    spread_homogenized: Optional[float] = Field(None, description="Homogenised spread")
    prev_close: Optional[float] = Field(None, description="Previous close price (Vortag)")
    open: Optional[float] = Field(None, description="Opening price (Eröffnung)")
    high: Optional[float] = Field(None, description="Intraday high (Hoch)")
    low: Optional[float] = Field(None, description="Intraday low (Tief)")


class WarrantAnalytics(BaseModel):
    """Greeks and derived key metrics (Kennzahlen) for a warrant."""

    delta: Optional[float] = Field(None, description="Delta")
    leverage: Optional[float] = Field(None, description="Leverage ratio (Hebel)")
    omega: Optional[float] = Field(None, description="Omega (effective leverage)")
    implied_volatility: Optional[float] = Field(None, description="Implied volatility in %")
    premium_per_annum: Optional[float] = Field(None, description="Time value cost per year in %")
    time_value: Optional[float] = Field(None, description="Time value (Zeitwert)")
    theta: Optional[float] = Field(None, description="Theta (time decay per day)")
    theoretical_value: Optional[float] = Field(None, description="Theoretical fair value")
    intrinsic_value: Optional[float] = Field(None, description="Intrinsic value (Innerer Wert)")
    break_even: Optional[float] = Field(None, description="Break-even price of the underlying")
    break_even_currency: Optional[str] = Field(None, description="Currency of the break-even price")
    moneyness: Optional[float] = Field(None, description="Moneyness")
    premium: Optional[float] = Field(None, description="Premium (Aufgeld) in %")
    vega: Optional[float] = Field(None, description="Vega (sensitivity to IV change)")
    gamma: Optional[float] = Field(None, description="Gamma (rate of change of delta)")


class WarrantReferenceData(BaseModel):
    """Static instrument attributes (Stammdaten) for a warrant."""

    isin: Optional[str] = Field(None, description="ISIN")
    wkn: Optional[str] = Field(None, description="WKN")
    last_trading_day: Optional[date] = Field(None, description="Last trading day (letzter Handelstag)")
    maturity_date: Optional[date] = Field(None, description="Maturity / expiry date (Fälligkeit)")
    strike: Optional[float] = Field(None, description="Strike price (Basispreis)")
    strike_currency: Optional[str] = Field(None, description="Currency of the strike price")
    underlying_name: Optional[str] = Field(None, description="Name of the underlying (Basiswert)")
    underlying_price: Optional[float] = Field(None, description="Current price of the underlying")
    underlying_price_currency: Optional[str] = Field(None, description="Currency of the underlying price")
    ratio: Optional[str] = Field(None, description="Subscription ratio (Bezugsverhältnis), e.g. '10 : 1'")
    warrant_type: Optional[str] = Field(None, description="Warrant type, e.g. 'Call (Amer.)'")
    issuer: Optional[str] = Field(None, description="Issuer name (Emittent)")
    currency: Optional[str] = Field(None, description="Settlement currency (Währung)")
    symbol: Optional[str] = Field(None, description="Comdirect Ticker symbol")


class WarrantDetailResponse(BaseModel):
    """Response envelope for GET /v1/warrants/{identifier}."""

    isin: str = Field(..., description="ISIN of the warrant")
    wkn: str = Field(..., description="WKN of the warrant")
    reference_data: WarrantReferenceData = Field(..., description="Static instrument attributes")
    market_data: WarrantMarketData = Field(..., description="Live price and quote data")
    analytics: WarrantAnalytics = Field(..., description="Greeks and key metrics")
