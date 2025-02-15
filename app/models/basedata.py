"""
Module: basedata
This module defines data models and validation logic for financial instruments using Pydantic and enumerations.
It includes classes for representing asset classes, trading notations, WKNs, ISINs, and base data for financial instruments.
The module also provides a function to validate ISINs using the Luhn algorithm.
Classes:
    AssetClass: Enumeration of different types of financial instruments.
    NotationType: Enumeration for different types of trading notations.
    Wkn: Represents a WKN (Wertpapierkennnummer) for a financial instrument.
    Isin: Represents an ISIN (International Securities Identification Number) for a financial instrument.
    BaseData: Represents the base data model for a financial instrument.
Functions:
    is_valid_isin(isin: str) -> bool: Check if the given ISIN is valid using the Luhn algorithm.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.logging_config import logger


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


class AssetClass(str, Enum):
    """
    AssetClass is an enumeration of different types of financial instruments.
    Each member of the enumeration represents a specific asset class.
    """

    STOCK = "Aktie"
    BOND = "Anleihe"
    ETF = "ETF"
    FONDS = "Fonds"
    WARRANT = "Optionsschein"
    CERTIFICATE = "Zertifikat"
    COMMODITY = "Rohstoff"
    INDEX = "Index"
    CURRENCY = "Währung"


class NotationType(str, Enum):
    """
    Enumeration for different types of trading notations.
    Attributes:
        LIFE_TRADING (str): Represents live trading.
        EXCH_TRADING (str): Represents exchange trading (Börse).
    """

    LIFE_TRADING = "LiveTrading"
    EXCH_TRADING = "Börse"


class BaseData(BaseModel):
    """
    BaseData model representing the basic data of a financial instrument.
    Attributes:
        name (str): Name of the financial instrument.
        wkn (Wkn): WKN of the financial instrument.
        isin (Optional[Isin]): ISIN of the financial instrument.
        symbol (Optional[str]): Symbol of the financial instrument, with a minimum length of 2 and a maximum length of 5.
        asset_class (AssetClass): The asset class of the financial instrument.
        id_notations_life_trading (Optional[dict[str, str]]): A dictionary of id_notations for the financial instrument in live trading.
        id_notations_exchange_trading (Optional[dict[str, str]]): A dictionary of id_notations for the financial instrument in exchange trading.
        preferred_id_notation_life_trading (Optional[str]): The preferred id_notation for live trading.
        preferred_id_notation_exchange_trading (Optional[str]): The preferred id_notation for exchange trading.
        default_id_notation (Optional[str]): The default id_notation for live trading.
    """

    name: str = Field(..., description="Name of the financial instrument")

    wkn: str = Field(
        ...,
        pattern=r"^[A-HJ-NPR-Z0-9]{6}$",
        description="WKN of the financial instrument",
    )

    isin: Optional[str] = Field(
        None,
        pattern=r"^[A-Z]{2}[A-Z0-9]{10}$",
        description="International Securities Identification Number",
    )

    symbol: Optional[str] = Field(
        None,
        description="Symbol of the financial instrument",
        min_length=2,
        max_length=5,
    )
    asset_class: AssetClass = Field(
        ...,
        description="The asset class of the financial instrument",
    )
    id_notations_life_trading: Optional[dict[str, str]] = Field(
        None,
        description="A dictionary of id_notations for the financial instrument",
    )
    id_notations_exchange_trading: Optional[dict[str, str]] = Field(
        None,
        description="A dictionary of id_notations for the financial instrument",
    )
    preferred_id_notation_life_trading: Optional[str] = Field(
        None,
        description="The preferred id_notation for live trading",
    )
    preferred_id_notation_exchange_trading: Optional[str] = Field(
        None,
        description="The preferred id_notation for exchange trading",
    )
    default_id_notation: Optional[str] = Field(
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
