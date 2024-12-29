from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


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


class InstrumentType(Enum):
    """
    Enum representing different types of financial instruments.
    """

    AKTIEN = "Aktie"
    ANLEIHEN = "Anleihe"
    ETFS = "ETF"
    FONDS = "Fonds"
    OPTIONSSCHEINE = "Optionsschein"
    ZERTIFIKATE = "Zertifikat"
    ROHSTOFFE = "Rohstoff"
    INDIZES = "Index"
    WAEHRUNGEN = "Währung"


class NotationType(Enum):
    """
    Enumeration for different types of trading notations.
    Attributes:
        LIFE_TRADING (str): Represents live trading.
        EXCH_TRADING (str): Represents exchange trading (Börse).
    """

    LIFE_TRADING = "LiveTrading"
    EXCH_TRADING = "Börse"


class InstrumentId(BaseModel):
    """
    InstrumentId model representing the identification details of a financial instrument.
    Attributes:
        name (str): Name of the financial instrument.
        wkn (str): German Wertpapierkennnummer (WKN), a six-character alphanumeric code.
        isin (str): International Securities Identification Number (ISIN), a twelve-character alphanumeric code.
        symbol (Optional[str]): Symbol of the instrument/security, default is None.
    """

    name: str = Field(..., description="Name of the financial instrument")
    wkn: str = Field(
        ...,
        pattern=r"^[A-HJ-NP-Z0-9]{6}$",
        description="German Wertpapierkennnummer",
    )
    isin: str = Field(
        ...,
        pattern=r"^[A-Z]{2}[A-Z0-9]{10}$",
        description="International Securities Identification Number",
    )
    symbol: Optional[str] = Field(
        ..., default_factory=None, description="Symbol of the financial instrument"
    )

    @field_validator("isin")
    @classmethod
    def isin_validator(cls, v: str) -> str:
        """
        Validate the ISIN (International Securities Identification Number) of the instrument.
        Args:
            v: The ISIN to validate.
        Returns:
            The validated ISIN.
        Raises:
            ValueError: If the ISIN is invalid.
        """

        if not is_valid_isin(v):
            raise ValueError("Invalid ISIN")
        return v


class NotationInfo(BaseModel):
    """
    Represents information about a notation.
    Attributes:
        notation_name (str): The name of the notation.
        notation_id (str): The unique identifier for the notation.
        notation_type (str): The type or category of the notation.
        notation_link (str): A URL link to more information about the notation.
    """

    notation_name: str
    notation_id: str
    notation_type: str
    notation_link: str


class NotationsList(BaseModel):
    """
    A class used to represent a list of notations.
    Attributes
    ----------
    notations_list : List[NotationInfo]
        A list containing notation information objects.
    """

    notations_list: List[NotationInfo]


class InstrumentBaseData(BaseModel):
    """
    InstrumentBaseData is a Pydantic model that represents the base data for an instrument.
    Attributes:
        instrument_id (InstrumentId): The unique identifier for the instrument.
        instrument_type (InstrumentType): The type/category of the instrument.
        instrument_notations (NotationsList): A list of notations associated with the instrument.
    """

    instrument_id: InstrumentId
    instrument_type: InstrumentType
    instrument_notations: NotationsList
