"""
Parser plugin for WARRANT asset class.

Warrants have a different HTML structure on comdirect and require special handling.
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
    extract_venues_from_dropdown,
    extract_wkn_from_h2,
)


class WarrantParser(BaseDataParser):
    """Parser for WARRANT asset class (Optionsscheine)."""
    
    @property
    def asset_class(self) -> AssetClass:
        """Return the asset class this parser handles."""
        return AssetClass.WARRANT
    
    def needs_id_notation_refetch(self) -> bool:
        """
        Warrants need to be refetched with ID_NOTATION to get complete info.
        
        When fetched with only WKN, the page redirects to an error page.
        We need to get the default ID_NOTATION first, then refetch.
        """
        return True
    
    def parse_name(self, soup: BeautifulSoup) -> str:
        """
        Extract the instrument name from the HTML.
        
        For warrants, the name is in the H1 tag with "Optionsschein" removed.
        """
        name = extract_from_h1(soup, remove_suffix="Optionsschein")
        if not name:
            raise ValueError("Could not find H1 headline")
        return name
    
    def parse_wkn(self, soup: BeautifulSoup) -> str:
        """
        Extract the WKN from the HTML.
        
        For warrants, WKN is in the H2 tag.
        """
        wkn = extract_wkn_from_h2(soup)
        if not wkn:
            raise ValueError("Could not extract WKN from H2")
        return wkn
    
    def parse_isin(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extract the ISIN from the HTML.
        
        For warrants, ISIN is in the H2 tag after "ISIN:"
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
        
        For warrants, trading venues are in #marketSelect dropdown.
        NOTE: This only works if the page was fetched WITH an ID_NOTATION parameter!
        
        Returns:
            Tuple of (lt_venue_dict, ex_venue_dict, 
                      preferred_lt_id_notation, preferred_ex_id_notation)
        """
        # Extract venues from dropdown
        id_notations_dict = extract_venues_from_dropdown(soup)
        
        if not id_notations_dict:
            # If we still don't have notations, return empty dicts
            # This can happen if the page wasn't fetched with ID_NOTATION
            return None, None, None, None
        
        # Separate into Life Trading and Exchange Trading
        lt_venue_dict, ex_venue_dict = categorize_lt_ex_venues(id_notations_dict)
        
        # Extract preferred ID_NOTATIONs based on liquidity
        # Use single-venue fallback for warrants
        preferred_lt_id_notation = extract_preferred_lt_notation(
            soup, lt_venue_dict, use_single_venue_fallback=True
        )
        preferred_ex_id_notation = extract_preferred_ex_notation(
            soup, ex_venue_dict, use_single_venue_fallback=True
        )
        
        return lt_venue_dict, ex_venue_dict, preferred_lt_id_notation, preferred_ex_id_notation
