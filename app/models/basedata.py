"""
This module defines data models and validation logic for financial instruments using Pydantic and enumerations.
Classes:
    AssetClass (StrEnum): Enumeration of different types of financial instruments.
    NotationType (Enum): Enumeration for different types of trading notations.
    NotationInfo (BaseModel): Represents information about a notation.
    NotationsList (BaseModel): Represents a list of notations.
    BaseData (BaseModel): Represents the base data model for a financial instrument.
Functions:
    is_valid_isin(isin: str) -> bool: Check if the given ISIN is valid using the Luhn algorithm.
"""

from enum import Enum, StrEnum
from typing import List, Optional

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


class AssetClass(StrEnum):
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


class NotationType(Enum):
    """
    Enumeration for different types of trading notations.
    Attributes:
        LIFE_TRADING (str): Represents live trading.
        EXCH_TRADING (str): Represents exchange trading (Börse).
    """

    LIFE_TRADING = "LiveTrading"
    EXCH_TRADING = "Börse"


class NotationInfo(BaseModel):
    """
    Represents information about a notation.
    Attributes:
        notation_name (str): The name of the notation.
        notation_id (str): The unique identifier for the notation.
        notation_link (str): A URL link to more information about the notation.
    """

    notation_name: str
    notation_id: str
    notation_link: str


class NotationsList(BaseModel):
    """
    Represents a list of notations.
    Attributes:
        notations_list (List[NotationInfo]): A list containing notation information.
    """

    notations_list: List[NotationInfo]


class BaseData(BaseModel):
    """
    BaseData represents the base data model for a financial instrument.
    Attributes:
        name (str): Name of the financial instrument.
        wkn (str): German Wertpapierkennnummer (WKN) with a specific pattern.
        isin (Optional[str]): International Securities Identification Number (ISIN) with a specific pattern.
        symbol (Optional[str]): Symbol of the financial instrument.
    Methods:
        isin_validator(cls, v: str) -> str: Validates the ISIN of the instrument.
    """

    name: str = Field(..., description="Name of the financial instrument")
    wkn: str = Field(
        ...,
        pattern=r"^[A-HJ-NP-Z0-9]{6}$",
        description="German Wertpapierkennnummer",
    )
    isin: Optional[str] = Field(
        None,
        # pattern=r"^[A-Z]{2}[A-Z0-9]{10}$",
        # default_factory=None,
        description="International Securities Identification Number",
    )
    symbol: Optional[str] = Field(
        ..., default_factory=None, description="Symbol of the financial instrument"
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
