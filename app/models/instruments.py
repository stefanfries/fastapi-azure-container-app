"""
Module: instruments
This module defines data models and validation logic for financial instruments using Pydantic and enumerations.
It includes classes for representing asset classes, trading notations, WKNs, ISINs, and instrument data for financial instruments.
The module also provides a function to validate ISINs using the Luhn algorithm.
Classes:
    AssetClass: Enumeration of different types of financial instruments.
    NotationType: Enumeration for different types of trading notations.
    GlobalIdentifiers: Consolidated global identifiers (ISIN, WKN, CUSIP, FIGI, symbols, OpenFIGI name).
    Instrument: Represents the master data model for a financial instrument.
Functions:
    is_valid_isin(isin: str) -> bool: Check if the given ISIN is valid using the Luhn algorithm.
"""

from enum import Enum, StrEnum

from pydantic import BaseModel, Field, field_validator
from pydantic_extra_types.currency_code import Currency

from app.core.logging import logger
from app.models.types import ISIN, WKN


def is_valid_isin(isin: str) -> bool:
    """
    Check if the given ISIN (International Securities Identification Number) is valid using the Luhn algorithm.
    The Luhn algorithm is a simple checksum formula used to validate a variety of identification numbers.
    Args:
        isin (str): The ISIN to be validated.
    Returns:
        bool: True if the ISIN is valid, False otherwise.
    """

    def char_to_digit(char: str) -> int:
        """
        Convert a character to its corresponding digit for the Luhn algorithm.
        """

        if char.isdigit():
            return int(char)
        return ord(char) - 55  # A=10, B=11, ..., Z=35

    digits = "".join(str(char_to_digit(char)) for char in isin)

    total = 0
    for i, digit in enumerate(reversed(digits)):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n

    return total % 10 == 0


class AssetClass(str, Enum):  # noqa: UP042 — custom __new__ incompatible with StrEnum
    """
    AssetClass is an enumeration of different types of financial instruments.

    Each member is defined as (value, comdirect_label) where:
        value:             English string serialized in the API response.
        comdirect_label:   German word used in comdirect HTML page titles
                           (e.g. "NVIDIA Aktie") for name extraction.
    """

    def __new__(cls, value: str, comdirect_label: str) -> "AssetClass":
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.comdirect_label = comdirect_label
        return obj

    STOCK = ("Stock", "Aktie")
    BOND = ("Bond", "Anleihe")
    ETF = ("ETF", "ETF")
    FONDS = ("Fund", "Fonds")
    WARRANT = ("Warrant", "Optionsschein")
    CERTIFICATE = ("Certificate", "Zertifikat")
    COMMODITY = ("Commodity", "Rohstoff")
    INDEX = ("Index", "Index")
    CURRENCY = ("Currency", "Währung")


class NotationType(StrEnum):
    """
    Enumeration for different types of trading notations.
    Attributes:
        LIFE_TRADING (str): Represents live trading.
        EXCH_TRADING (str): Represents exchange trading (Börse).
    """

    LIFE_TRADING = "LiveTrading"
    EXCH_TRADING = "Börse"


class GlobalIdentifiers(BaseModel):
    """
    Consolidated view of all global identifiers for a financial instrument.

    Attributes:
        isin: International Securities Identification Number.
        wkn: German Wertpapierkennnummer (primary key).
        cusip: US/CA Committee on Uniform Securities Identification Procedures number.
               Derived from the ISIN for US instruments (ISIN chars 2–10); None otherwise.
        figi: Composite Financial Instrument Global Identifier from OpenFIGI (BBG…).
              Identifies the instrument across all trading venues within one country.
        symbol_comdirect: Ticker symbol as displayed on comdirect.de.
        symbol_yfinance: Ticker symbol for use with the yfinance library, including the
                         Yahoo Finance exchange suffix (e.g. "NVDA", "SIE.DE").
                         None for asset classes not supported by Yahoo Finance
                         (WARRANT, CERTIFICATE).
        name_openfigi: Instrument name as returned by the OpenFIGI API (e.g. "NVIDIA CORP").
                       None when enrichment is skipped or no match is found.
    """

    isin: ISIN | None = Field(None, description="ISIN")
    wkn: WKN = Field(..., description="German WKN")
    cusip: str | None = Field(None, description="CUSIP (US/CA instruments only)")
    figi: str | None = Field(None, description="Composite FIGI from OpenFIGI")
    symbol_comdirect: str | None = Field(None, description="Ticker symbol on comdirect")
    symbol_yfinance: str | None = Field(None, description="Ticker symbol for yfinance")
    name_openfigi: str | None = Field(None, description="Instrument name from OpenFIGI")


class VenueInfo(BaseModel):
    """
    Trading venue entry combining id_notation and inferred currency.

    Attributes:
        id_notation (str): The comdirect ID_NOTATION for this venue.
        currency (Optional[str]): ISO 4217 currency code inferred from the venue name.
            None when the venue is not in the known lookup table and carries no
            explicit currency suffix (e.g. "SIX SWISS (USD)").
    """

    id_notation: str
    currency: Currency | None = None


class Instrument(BaseModel):
    """
    Instrument model representing the master data of a financial instrument.
    Attributes:
        name (str): Name of the financial instrument.
        wkn (str): WKN of the financial instrument.
        isin (Optional[str]): ISIN of the financial instrument.
        asset_class (AssetClass): The asset class of the financial instrument (English value, e.g. "Stock").
        global_identifiers (Optional[GlobalIdentifiers]): Consolidated global identifiers including
            ISIN, WKN, CUSIP, FIGI, ticker symbols, and OpenFIGI name.
        id_notations_life_trading (Optional[dict[str, VenueInfo]]): Life-trading venues mapping
            venue name to VenueInfo (id_notation + currency).
        id_notations_exchange_trading (Optional[dict[str, VenueInfo]]): Exchange-trading venues
            mapping venue name to VenueInfo (id_notation + currency).
        preferred_id_notation_life_trading (Optional[str]): The preferred id_notation for live trading.
        preferred_id_notation_exchange_trading (Optional[str]): The preferred id_notation for exchange trading.
        default_id_notation (Optional[str]): The default id_notation for live trading.
    """

    name: str = Field(..., description="Name of the financial instrument")

    wkn: WKN = Field(..., description="WKN of the financial instrument")

    isin: ISIN | None = Field(None, description="International Securities Identification Number")

    asset_class: AssetClass = Field(
        ...,
        description="The asset class of the financial instrument",
    )
    global_identifiers: GlobalIdentifiers | None = Field(
        None,
        description="Consolidated global identifiers (ISIN, WKN, CUSIP, FIGI, symbols)",
    )
    id_notations_life_trading: dict[str, VenueInfo] | None = Field(
        None,
        description="Life-trading venues mapping venue name to VenueInfo (id_notation + currency)",
    )
    id_notations_exchange_trading: dict[str, VenueInfo] | None = Field(
        None,
        description="Exchange-trading venues mapping venue name to VenueInfo (id_notation + currency)",
    )
    preferred_id_notation_life_trading: str | None = Field(
        None,
        description="The preferred id_notation for live trading",
    )
    preferred_id_notation_exchange_trading: str | None = Field(
        None,
        description="The preferred id_notation for exchange trading",
    )
    default_id_notation: str | None = Field(
        None,
        description="The default id_notation for live trading",
    )

    @field_validator("isin")
    @classmethod
    def isin_validator(cls, v: str) -> str | None:
        """
        Validate the ISIN (International Securities Identification Number) of the instrument.
        Args:
            v: The ISIN to validate.
        Returns:
            The validated ISIN.
        Raises:
            ValueError: If the ISIN is invalid.
        """
        if v is not None and not is_valid_isin(v):
            logger.error("Invalid ISIN: %s", v)
            raise ValueError("Invalid ISIN")
        return v
