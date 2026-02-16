"""
Parser plugin for STOCK asset class.

This parser handles the standard HTML structure used by stocks, bonds, ETFs,
and funds on comdirect.
"""


from typing import Dict, Optional, Tuple

from bs4 import BeautifulSoup

from app.models.basedata import AssetClass
from app.parsers.plugins.base_parser import BaseDataParser
from app.parsers.plugins.parsing_utils import (
    categorize_lt_ex_venues,
    extract_after_label,
    extract_from_h1,
    extract_preferred_ex_notation,
    extract_preferred_lt_notation,
    extract_venue_from_single_table,
    extract_venues_from_dropdown,
    extract_wkn_from_h2,
)


class StockParser(BaseDataParser):
    """Parser for STOCK, BOND, ETF, FONDS, and CERTIFICATE asset classes."""
    
    def __init__(self, asset_class: AssetClass):
        """
        Initialize the parser for a specific asset class.
        
        Args:
            asset_class: The asset class this parser will handle
        """
        self._asset_class = asset_class
    
    @property
    def asset_class(self) -> AssetClass:
        """Return the asset class this parser handles."""
        return self._asset_class
    
    def needs_id_notation_refetch(self) -> bool:
        """
        Standard assets need to be refetched with ID_NOTATION to get trading venues.
        
        When fetched with only WKN, comdirect redirects to an error page.
        We need the default ID_NOTATION from the first request, then refetch
        to get the complete trading venue information.
        """
        return True
    
    def parse_name(self, soup: BeautifulSoup) -> str:
        """
        Extract the instrument name from the HTML.
        
        For standard assets, the name is in the H1 tag with the asset class
        name removed.
        """
        name = extract_from_h1(soup, remove_suffix=self.asset_class.value)
        if not name:
            raise ValueError("Could not find H1 headline")
        return name
    
    def parse_wkn(self, soup: BeautifulSoup) -> str:
        """
        Extract the WKN from the HTML.
        
        For standard assets, WKN is in the H2 tag, extracted from patterns like:
        "WKN: 123456 / ISIN: DE0001234567"
        """
        wkn = extract_wkn_from_h2(soup)
        if not wkn:
            raise ValueError("Could not extract WKN from H2")
        return wkn
    
    def parse_isin(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the ISIN from the HTML.
        
        For standard assets, ISIN is in the H2 tag after "ISIN:"
        """
        return extract_after_label(soup, "ISIN:", max_length=12)
    
    def parse_id_notations(
        self,
        soup: BeautifulSoup,
        default_id_notation: Optional[str] = None
    ) -> Tuple[
        Optional[Dict[str, str]], 
        Optional[Dict[str, str]],
        Optional[str],
        Optional[str]
    ]:
        """
        Extract trading venues and their ID_NOTATIONs from the HTML,
        including preferred notations based on liquidity.
        
        For standard assets, trading venues are in #marketSelect dropdown
        or in a table if there's only one venue.
        
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
