"""
Base parser interface for asset class-specific parsing.

This module defines the abstract base class for all asset class parsers,
implementing a plugin pattern for extensibility.
"""

from abc import ABC, abstractmethod

from bs4 import BeautifulSoup

from app.models.instrument_details import InstrumentDetails
from app.models.instruments import AssetClass


class InstrumentParser(ABC):
    """
    Abstract base class for asset class-specific parsers.

    Each asset class (STOCK, WARRANT, ETF, etc.) should have its own parser
    that implements this interface.
    """

    @property
    @abstractmethod
    def asset_class(self) -> AssetClass:
        """Return the asset class this parser handles."""
        pass

    @abstractmethod
    def parse_name(self, soup: BeautifulSoup) -> str:
        """
        Extract the instrument name from the HTML.

        Args:
            soup: BeautifulSoup object containing the instrument page HTML

        Returns:
            The instrument name
        """
        pass

    @abstractmethod
    def parse_wkn(self, soup: BeautifulSoup) -> str:
        """
        Extract the WKN (Wertpapierkennnummer) from the HTML.

        Args:
            soup: BeautifulSoup object containing the instrument page HTML

        Returns:
            The WKN
        """
        pass

    @abstractmethod
    def parse_isin(self, soup: BeautifulSoup) -> str | None:
        """
        Extract the ISIN from the HTML.

        Args:
            soup: BeautifulSoup object containing the instrument page HTML

        Returns:
            The ISIN if available, None otherwise
        """
        pass

    @abstractmethod
    def parse_id_notations(
        self, soup: BeautifulSoup, default_id_notation: str | None = None
    ) -> tuple[dict[str, str] | None, dict[str, str] | None, str | None, str | None]:
        """
        Extract trading venues and their ID_NOTATIONs from the HTML.

        Args:
            soup: BeautifulSoup object containing the instrument page HTML
            default_id_notation: The default ID_NOTATION from the URL (if available)

        Returns:
            Tuple of (life_trading_dict, exchange_trading_dict,
                      preferred_lt_id_notation, preferred_ex_id_notation)
            - life_trading_dict: Maps trading venue name to ID_NOTATION
            - exchange_trading_dict: Maps trading venue name to ID_NOTATION
            - preferred_lt_id_notation: ID_NOTATION with highest "Gestellte Kurse"
            - preferred_ex_id_notation: ID_NOTATION with highest "Anzahl Kurse"
        """
        pass

    def parse_details(self, soup: BeautifulSoup) -> InstrumentDetails | None:
        """
        Extract asset-class-specific reference data (Stammdaten) from the HTML.

        Subclasses override this method to populate the appropriate
        ``InstrumentDetails`` variant.  The default implementation returns
        ``None`` so that parsers that have not yet been extended remain valid.

        Args:
            soup: BeautifulSoup object containing the instrument page HTML

        Returns:
            A populated ``InstrumentDetails`` instance, or ``None`` when not
            implemented for this asset class.
        """
        return None
