"""
Parser plugin for WARRANT asset class.

Warrants have a different HTML structure on comdirect and require special handling.
"""

import re
from typing import Dict, Optional, Tuple

from bs4 import BeautifulSoup

from app.models.basedata import AssetClass
from app.parsers.plugins.base_parser import BaseDataParser
from app.parsers.plugins.parsing_utils import (
    clean_numeric_value,
    extract_after_label,
    extract_from_h1,
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
        id_notations_dict = {}
        
        # Look for the market select dropdown
        market_select = soup.select_one("#marketSelect")
        
        if market_select:
            options = market_select.find_all("option")
            
            for option in options:
                value = option.get("value", "")
                text = option.get_text(strip=True)
                
                if value and text:
                    id_notations_dict[text] = value
        
        if not id_notations_dict:
            # If we still don't have notations, return empty dicts
            # This can happen if the page wasn't fetched with ID_NOTATION
            return None, None, None, None
        
        # For warrants, we need to categorize venues as Life Trading or Exchange Trading
        # Life Trading typically starts with "LT" prefix
        # Exchange Trading is regular stock exchange names
        
        lt_venue_dict = {}
        ex_venue_dict = {}
        
        for venue, notation in id_notations_dict.items():
            if venue.startswith("LT "):
                # Life Trading venue
                lt_venue_dict[venue] = notation
            else:
                # Exchange Trading venue
                ex_venue_dict[venue] = notation
        
        # Extract preferred ID_NOTATIONs based on liquidity
        # Warrants may have similar table structure to stocks
        preferred_lt_id_notation = self._extract_preferred_lt_notation(soup, lt_venue_dict)
        preferred_ex_id_notation = self._extract_preferred_ex_notation(soup, ex_venue_dict)
        
        return lt_venue_dict, ex_venue_dict, preferred_lt_id_notation, preferred_ex_id_notation
    
    def _extract_id_notation_from_data_plugin(self, data_plugin_str: str) -> Optional[str]:
        """
        Extract ID_NOTATION from data-plugin attribute.
        
        Args:
            data_plugin_str: The data-plugin attribute value
            
        Returns:
            The extracted ID_NOTATION, or None if not found
        """
        match = re.search(r'ID_NOTATION=(\d+)', data_plugin_str)
        if match:
            return match.group(1)
        return None
    
    def _extract_preferred_lt_notation(
        self, 
        soup: BeautifulSoup, 
        lt_venue_dict: Dict[str, str]
    ) -> Optional[str]:
        """
        Extract preferred Life Trading ID_NOTATION based on highest "Gestellte Kurse".
        
        Args:
            soup: BeautifulSoup object containing the instrument page HTML
            lt_venue_dict: Dictionary mapping venue names to ID_NOTATIONs
            
        Returns:
            The ID_NOTATION with highest "Gestellte Kurse", or None if not found
        """
        if not lt_venue_dict:
            return None
        
        # If only one Life Trading venue, return it as preferred
        if len(lt_venue_dict) == 1:
            return list(lt_venue_dict.values())[0]
        
        # Find the Life Trading table (contains "Gestellte Kurse" column)
        tables = soup.find_all("table")
        
        for table in tables:
            headers = table.find_all("th")
            header_texts = [h.get_text(strip=True) for h in headers]
            
            if "Gestellte" in " ".join(header_texts) or "LiveTrading" in header_texts:
                # Build mapping: venue_name -> id_notation from headers
                venue_to_id = {}
                for header in headers:
                    link = header.find("a")
                    if link:
                        data_plugin = link.get("data-plugin", "")
                        if "ID_NOTATION=" in data_plugin:
                            venue_name = header.get_text(strip=True)
                            id_not = self._extract_id_notation_from_data_plugin(data_plugin)
                            if venue_name and id_not:
                                venue_to_id[venue_name] = id_not
                
                # Extract liquidity values from tbody
                tbody = table.find("tbody")
                if tbody:
                    rows = tbody.find_all("tr")
                    
                    lt_venues_with_liquidity = []
                    for row in rows:
                        cells = row.find_all("td")
                        if not cells:
                            continue
                        
                        # Get venue name from first cell's data-label
                        venue_name = cells[0].get("data-label", "")
                        
                        # Get "Gestellte Kurse" value
                        gestellte_value = None
                        for cell in cells:
                            if cell.get("data-label") == "Gestellte Kurse":
                                gestellte_text = cell.get_text(strip=True)
                                # Convert using utility (handles "6.844" and "3,10 Mio.")
                                gestellte_value = clean_numeric_value(gestellte_text)
                                if gestellte_value is None:
                                    gestellte_value = 0
                                break
                        
                        # Match venue name to ID_NOTATION
                        id_not = venue_to_id.get(venue_name)
                        
                        if venue_name and id_not and gestellte_value is not None:
                            lt_venues_with_liquidity.append({
                                "venue": venue_name,
                                "id_notation": id_not,
                                "gestellte_kurse": gestellte_value
                            })
                    
                    # Find preferred (highest gestellte_kurse)
                    if lt_venues_with_liquidity:
                        preferred_lt = max(lt_venues_with_liquidity, key=lambda x: x["gestellte_kurse"])
                        return preferred_lt["id_notation"]
                
                break
        
        # If no table found, return first venue as fallback
        return list(lt_venue_dict.values())[0] if lt_venue_dict else None
    
    def _extract_preferred_ex_notation(
        self, 
        soup: BeautifulSoup, 
        ex_venue_dict: Dict[str, str]
    ) -> Optional[str]:
        """
        Extract preferred Exchange Trading ID_NOTATION based on highest "Anzahl Kurse".
        
        Args:
            soup: BeautifulSoup object containing the instrument page HTML
            ex_venue_dict: Dictionary mapping venue names to ID_NOTATIONs
            
        Returns:
            The ID_NOTATION with highest "Anzahl Kurse", or None if not found
        """
        if not ex_venue_dict:
            return None
        
        # If only one Exchange Trading venue, return it as preferred
        if len(ex_venue_dict) == 1:
            return list(ex_venue_dict.values())[0]
        
        # Find the Exchange Trading table (contains "Anzahl Kurse" column)
        tables = soup.find_all("table")
        
        for table in tables:
            headers = table.find_all("th")
            header_texts = [h.get_text(strip=True) for h in headers]
            
            if "Anzahl Kurse" in header_texts:
                # Build mapping: venue_name -> id_notation from headers
                venue_to_id = {}
                for header in headers:
                    link = header.find("a")
                    if link:
                        data_plugin = link.get("data-plugin", "")
                        if "ID_NOTATION=" in data_plugin:
                            venue_name = header.get_text(strip=True)
                            id_not = self._extract_id_notation_from_data_plugin(data_plugin)
                            if venue_name and id_not:
                                venue_to_id[venue_name] = id_not
                
                # Extract liquidity values from tbody
                tbody = table.find("tbody")
                if tbody:
                    rows = tbody.find_all("tr")
                    
                    ex_venues_with_liquidity = []
                    for row in rows:
                        cells = row.find_all("td")
                        if not cells:
                            continue
                        
                        # Get venue name
                        venue_name = cells[0].get("data-label", "")
                        
                        # Get "Anzahl Kurse" value
                        anzahl_value = None
                        for cell in cells:
                            if cell.get("data-label") == "Anzahl Kurse":
                                anzahl_text = cell.get_text(strip=True)
                                # Convert using utility (handles "18.087" and "3,10 Mio.")
                                anzahl_value = clean_numeric_value(anzahl_text)
                                if anzahl_value is None:
                                    anzahl_value = 0
                                break
                        
                        # Match to ID_NOTATION
                        id_not = venue_to_id.get(venue_name)
                        
                        if venue_name and id_not and anzahl_value is not None:
                            ex_venues_with_liquidity.append({
                                "venue": venue_name,
                                "id_notation": id_not,
                                "anzahl_kurse": anzahl_value
                            })
                    
                    # Find preferred (highest anzahl_kurse)
                    if ex_venues_with_liquidity:
                        preferred_ex = max(ex_venues_with_liquidity, key=lambda x: x["anzahl_kurse"])
                        return preferred_ex["id_notation"]
                
                break
        
        # If no table found, return first venue as fallback
        return list(ex_venue_dict.values())[0] if ex_venue_dict else None
