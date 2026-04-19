"""
Parser plugin for special (non-tradeable) asset classes: INDEX, COMMODITY, CURRENCY.

These instruments are not directly tradeable — they are only accessible via
derivative products such as warrants, certificates, or ETFs. Consequently they
have no trading venues and no id_notations on comdirect.

HTML differences vs. standard assets:
    - WKN is at position 2 in the H2 text (e.g. "WKN WKN846900") instead of position 1.
    - No ISIN is shown on the page.
    - No #marketSelect dropdown and no venue table.
"""

from typing import Dict, Optional, Tuple

from bs4 import BeautifulSoup

from app.models.instruments import AssetClass, VenueInfo
from app.parsers.plugins.base_parser import InstrumentParser
from app.parsers.plugins.parsing_utils import extract_name_from_h1, extract_wkn_from_h2


class SpecialAssetParser(InstrumentParser):
    """
    Parser for INDEX, COMMODITY, and CURRENCY asset classes.

    These asset classes share a slightly different comdirect HTML layout from
    standard assets and carry no trading-venue or id_notation information.
    """

    def __init__(self, asset_class: AssetClass) -> None:
        """
        Initialise the parser for a specific special asset class.

        Args:
            asset_class: One of AssetClass.INDEX, AssetClass.COMMODITY, or AssetClass.CURRENCY.
        """
        self._asset_class = asset_class

    @property
    def asset_class(self) -> AssetClass:
        """Return the asset class this parser handles."""
        return self._asset_class

    def parse_name(self, soup: BeautifulSoup) -> str:
        """
        Extract the instrument name from the H1 element.

        The comdirect H1 for special assets looks like e.g. "DAX Index" or
        "Gold Rohstoff". The asset-class label is kept as part of the name.
        """
        name = extract_name_from_h1(soup)
        if not name:
            raise ValueError("Could not find H1 headline")
        return name

    def parse_wkn(self, soup: BeautifulSoup) -> str:
        """
        Extract the WKN from the H2 element.

        For special assets the WKN sits at position 2 in the H2 token list
        (e.g. ['WKN', 'WKN846900'] → ['WKN', 'WKN', '846900']), unlike
        standard assets where it is at position 1.
        """
        wkn = extract_wkn_from_h2(soup, position_offset=2)
        if not wkn:
            raise ValueError("Could not extract WKN from H2")
        return wkn

    def parse_isin(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Always returns None — special assets have no ISIN on comdirect.
        """
        return None

    def parse_id_notations(
        self,
        soup: BeautifulSoup,
        default_id_notation: Optional[str] = None,
    ) -> Tuple[
        Optional[Dict[str, VenueInfo]],
        Optional[Dict[str, VenueInfo]],
        Optional[str],
        Optional[str],
    ]:
        """
        Always returns (None, None, None, None).

        Special assets (indices, commodities, currencies) are not directly
        tradeable and therefore have no trading venues or id_notations.
        """
        return None, None, None, None
