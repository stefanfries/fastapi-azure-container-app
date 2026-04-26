"""
Abstract base parser for tradeable standard asset classes.

Provides shared implementations of parse_name, parse_wkn, parse_isin,
parse_id_notations, and helper utilities _parse_date / _split_value_currency.

Concrete subclasses (StockParser, BondParser, ETFParser, FondsParser,
CertificateParser, WarrantParser) each implement asset_class and parse_details.
"""

from abc import abstractmethod
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.models.instruments import AssetClass, VenueInfo
from app.parsers.base_parser import InstrumentParser
from app.parsers.plugins.parsing_utils import (
    categorize_lt_ex_venues,
    clean_float_value,
    extract_after_label,
    extract_name_from_h1,
    extract_preferred_ex_notation,
    extract_preferred_lt_notation,
    extract_venue_from_single_table,
    extract_venues_from_dropdown,
    extract_wkn_from_h2,
)


class StandardAssetParser(InstrumentParser):
    """
    Abstract base parser for all tradeable standard asset classes
    (STOCK, BOND, ETF, FONDS, CERTIFICATE, WARRANT).

    Provides shared implementations for the methods that are identical across
    all tradeable asset classes.  Concrete subclasses must implement:
        - ``asset_class`` property (returns the specific AssetClass member)
        - ``parse_details()`` (asset-class-specific Stammdaten extraction)
    """

    @property
    @abstractmethod
    def asset_class(self) -> AssetClass:
        """Return the asset class this parser handles."""

    def parse_name(self, soup: BeautifulSoup) -> str:
        """
        Extract the instrument name from the HTML.

        For standard assets, the name is in the H1 tag with the asset class
        name removed.
        """
        name = extract_name_from_h1(soup, remove_suffix=self.asset_class.comdirect_label)
        if not name:
            raise ValueError("Could not find H1 headline")
        return name

    def parse_wkn(self, soup: BeautifulSoup) -> str | None:
        """
        Extract the WKN from the HTML.

        For standard assets, WKN is in the H2 tag, extracted from patterns like:
        "WKN: 123456 / ISIN: DE0001234567"
        Returns None for foreign instruments where WKN is '--'.
        """
        return extract_wkn_from_h2(soup)

    def parse_isin(self, soup: BeautifulSoup) -> str | None:
        """
        Extract the ISIN from the HTML.

        For standard assets, ISIN is in the H2 tag after "ISIN:"
        """
        return extract_after_label(soup, "ISIN:", max_length=12)

    def parse_id_notations(
        self, soup: BeautifulSoup, default_id_notation: str | None = None
    ) -> tuple[dict[str, VenueInfo] | None, dict[str, VenueInfo] | None, str | None, str | None]:
        """
        Extract trading venues and their ID_NOTATIONs from the HTML,
        including preferred notations based on liquidity.

        For standard assets, trading venues are in the #marketSelect dropdown
        or in a table if there's only one venue. comdirect always redirects any
        instrument lookup to a URL with ID_NOTATION already appended (platform-wide
        behaviour), so the dropdown is always populated.

        Returns:
            Tuple of (lt_venue_dict, ex_venue_dict,
                      preferred_lt_id_notation, preferred_ex_id_notation)
        """
        # Try dropdown first (multiple venues)
        id_notations_dict = extract_venues_from_dropdown(soup)

        # If no dropdown, try single-venue table
        if not id_notations_dict:
            id_notations_dict = extract_venue_from_single_table(soup)

        # Separate into Life Trading and Exchange Trading
        lt_venue_dict, ex_venue_dict = categorize_lt_ex_venues(id_notations_dict)

        # Extract preferred ID_NOTATIONs based on liquidity
        preferred_lt_id_notation = extract_preferred_lt_notation(soup, lt_venue_dict)
        preferred_ex_id_notation = extract_preferred_ex_notation(soup, ex_venue_dict)

        return lt_venue_dict, ex_venue_dict, preferred_lt_id_notation, preferred_ex_id_notation

    # ------------------------------------------------------------------
    # Shared helpers used by the concrete detail parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(text: str | None) -> date | None:
        """Parse a German date string (DD.MM.YYYY or DD.MM.YY) into a date object."""
        if not text or text.strip() in ("--", "k. A.", ""):
            return None
        for fmt in ("%d.%m.%Y", "%d.%m.%y"):
            try:
                return datetime.strptime(text.strip(), fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _split_value_currency(raw: str | None) -> tuple[float | None, str | None]:
        """Split a string like '100,00 EUR' into (100.0, 'EUR')."""
        if not raw or raw.strip() in ("--", ""):
            return None, None
        parts = raw.split()
        currency: str | None = None
        if parts and len(parts[-1]) == 3 and parts[-1].isupper():
            currency = parts[-1]
            raw = " ".join(parts[:-1])
        value = clean_float_value(raw)
        return value, currency

