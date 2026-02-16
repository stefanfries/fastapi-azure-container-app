"""
Parsing utility functions for common HTML extraction patterns.

This module provides reusable parsing functions that can be shared across
different asset class parsers, promoting DRY principles and consistency.
"""

import re
from typing import Dict, Optional, Tuple

from bs4 import BeautifulSoup


def extract_from_h2_position(soup: BeautifulSoup, position: int) -> Optional[str]:
    """
    Extract a value from a specific position in the H2 text after splitting by whitespace.
    
    Args:
        soup: BeautifulSoup object containing the HTML
        position: Zero-based index of the desired token after splitting H2 text
        
    Returns:
        The extracted value or None if H2 not found or position invalid
        
    Example:
        H2 text: "WKN: 918422 ISIN: US67066G1040"
        extract_from_h2_position(soup, 1) -> "918422"
        extract_from_h2_position(soup, 3) -> "US67066G1040"
    """
    headline_h2 = soup.select_one("h2")
    if not headline_h2:
        return None
    
    h2_parts = headline_h2.text.strip().split()
    if len(h2_parts) <= position:
        return None
    
    return h2_parts[position]


def extract_after_label(soup: BeautifulSoup, label: str, max_length: Optional[int] = None) -> Optional[str]:
    """
    Extract text that appears after a specific label in the H2 element.
    
    Args:
        soup: BeautifulSoup object containing the HTML
        label: The label to search for (e.g., "ISIN:", "WKN:")
        max_length: Optional maximum length to validate the extracted value
        
    Returns:
        The extracted value or None if not found or invalid
        
    Example:
        H2 text: "WKN: 918422\nISIN: US67066G1040"
        extract_after_label(soup, "ISIN:") -> "US67066G1040"
        extract_after_label(soup, "ISIN:", max_length=12) -> "US67066G1040" (validated)
    """
    headline_h2 = soup.select_one("h2")
    if not headline_h2:
        return None
    
    h2_text = headline_h2.text
    
    # Check if label exists in the text
    if label not in h2_text:
        # Try without colon
        label_without_colon = label.rstrip(":")
        if label_without_colon not in h2_text.upper() and label_without_colon.upper() not in h2_text.upper():
            return None
        label = label_without_colon
    
    # Extract text after the label
    if ":" in label:
        text_after_label = h2_text.split(label)[-1]
    else:
        # Case-insensitive search
        parts = h2_text.upper().split(label.upper())
        if len(parts) < 2:
            return None
        # Find the position in original text
        label_pos = h2_text.upper().index(label.upper())
        text_after_label = h2_text[label_pos + len(label):]
    
    # Clean up and extract first token
    value = text_after_label.strip().split()[0] if text_after_label.strip() else None
    
    # Validate length if specified
    if value and max_length and len(value) != max_length:
        return None
    
    return value


def extract_from_h1(soup: BeautifulSoup, remove_suffix: Optional[str] = None) -> Optional[str]:
    """
    Extract text from H1 element, optionally removing a suffix.
    
    Args:
        soup: BeautifulSoup object containing the HTML
        remove_suffix: Optional suffix to remove from the H1 text (e.g., asset class name)
        
    Returns:
        The extracted and cleaned text or None if H1 not found
        
    Example:
        H1 text: "NVIDIA Aktie"
        extract_from_h1(soup, "Aktie") -> "NVIDIA"
    """
    headline_h1 = soup.select_one("h1")
    if not headline_h1:
        return None
    
    text = headline_h1.text.strip()
    
    if remove_suffix:
        text = text.replace(remove_suffix, "").strip()
    
    return text


def extract_table_cell_by_label(soup: BeautifulSoup, table_header: str, cell_label: str) -> Optional[str]:
    """
    Extract a cell value from a table by finding a header and then a specific label.
    
    Args:
        soup: BeautifulSoup object containing the HTML
        table_header: Text pattern to find the table section (e.g., "Aktieninformationen")
        cell_label: Label of the cell to extract (e.g., "Symbol")
        
    Returns:
        The extracted cell value or None if not found
        
    Example:
        extract_table_cell_by_label(soup, "Aktieninformationen", "Symbol") -> "NVD"
    """
    import re
    
    # Find the section containing the table
    section = soup.find(text=re.compile(table_header))
    if not section:
        return None
    
    # Navigate to find the label
    table_section = section.parent.parent
    row = table_section.find("th", text=re.compile(cell_label))
    
    if not row:
        return None
    
    # Get the sibling cell value
    cell = row.find_next_sibling("td")
    if cell:
        return cell.text.strip()
    
    return None


def clean_numeric_value(value: str) -> Optional[int]:
    """
    Clean and convert a numeric string to integer, handling German format with suffixes.
    
    Args:
        value: String containing a number (may have dots, commas, suffixes like Mio., Mrd., etc.)
        
    Returns:
        Integer value or None if conversion fails
        
    Example:
        clean_numeric_value("1.234") -> 1234
        clean_numeric_value("1,234") -> 1234
        clean_numeric_value("3,10 Mio.") -> 3100000
        clean_numeric_value("42,34 Mrd.") -> 42340000000
        clean_numeric_value("51,11 Mio.") -> 51110000
    """
    if not value or value.strip() == "--":
        return None
    
    try:
        value = value.strip()
        
        # Check for magnitude suffixes (German format)
        multiplier = 1
        if "Mrd." in value or "Mrd" in value:
            # Billion (Milliarde)
            multiplier = 1_000_000_000
            value = value.replace("Mrd.", "").replace("Mrd", "").strip()
        elif "Mio." in value or "Mio" in value:
            # Million
            multiplier = 1_000_000
            value = value.replace("Mio.", "").replace("Mio", "").strip()
        elif "Tsd." in value or "Tsd" in value:
            # Thousand (Tausend)
            multiplier = 1_000
            value = value.replace("Tsd.", "").replace("Tsd", "").strip()
        
        # Handle German number format: "3,10" means 3.10 (comma is decimal separator)
        # and "1.234" means 1234 (dot is thousand separator)
        if "," in value:
            # Has decimal separator - convert to float first
            value = value.replace(".", "")  # Remove thousand separators
            value = value.replace(",", ".")  # Convert decimal separator
            numeric_value = float(value)
        else:
            # Only thousand separators
            value = value.replace(".", "")  # Remove thousand separators
            numeric_value = int(value)
        
        # Apply multiplier and convert to integer
        return int(numeric_value * multiplier)
        
    except (ValueError, AttributeError):
        return None


def extract_wkn_from_h2(soup: BeautifulSoup, position_offset: int = 1) -> Optional[str]:
    """
    Extract WKN from H2 element at a specific position offset.
    
    This is a specialized version of extract_from_h2_position for WKN extraction,
    with validation and error handling.
    
    Args:
        soup: BeautifulSoup object containing the HTML
        position_offset: Position offset in the split H2 text (default: 1 for standard assets)
        
    Returns:
        The WKN value or None if not found
        
    Example:
        H2 text: "WKN: 918422 ISIN: US67066G1040"
        extract_wkn_from_h2(soup, 1) -> "918422"
    """
    headline_h2 = soup.select_one("h2")
    if not headline_h2:
        return None
    
    h2_text = headline_h2.text.strip()
    h2_parts = h2_text.split()
    
    if len(h2_parts) <= position_offset:
        return None
    
    wkn = h2_parts[position_offset]
    
    # Clean up any remaining whitespace or newlines
    wkn = wkn.split()[0] if wkn.split() else wkn
    
    return wkn


def extract_id_notation_from_data_plugin(data_plugin_str: str) -> Optional[str]:
    """
    Extract ID_NOTATION from data-plugin attribute.
    
    Args:
        data_plugin_str: The data-plugin attribute value
        
    Returns:
        The extracted ID_NOTATION, or None if not found
        
    Example:
        extract_id_notation_from_data_plugin("...ID_NOTATION=123456...") -> "123456"
    """
    match = re.search(r'ID_NOTATION=(\d+)', data_plugin_str)
    if match:
        return match.group(1)
    return None


def extract_venues_from_dropdown(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extract trading venues and their ID_NOTATIONs from #marketSelect dropdown.
    
    Args:
        soup: BeautifulSoup object containing the instrument page HTML
        
    Returns:
        Dictionary mapping venue names to ID_NOTATIONs
        
    Example:
        {"Xetra": "123456", "Frankfurt": "789012"}
    """
    id_notations_dict = {}
    
    # Look for the market select dropdown
    market_select = soup.select_one("#marketSelect")
    
    if market_select:
        options = market_select.find_all("option")
        
        for option in options:
            # Try label/value first (stock structure)
            label = option.get("label", "")
            value = option.get("value", "")
            
            if label and value:
                id_notations_dict[label] = value
            else:
                # Try text/value (warrant structure)
                text = option.get_text(strip=True)
                value = option.get("value", "")
                if text and value:
                    id_notations_dict[text] = value
    
    return id_notations_dict


def extract_venue_from_single_table(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extract single trading venue from .simple-table structure.
    
    This is used when there's only one trading venue available and no dropdown.
    
    Args:
        soup: BeautifulSoup object containing the instrument page HTML
        
    Returns:
        Dictionary with single venue name and ID_NOTATION
        
    Example:
        {"Tradegate": "123456"}
    """
    id_notations_dict = {}
    
    # Look for single-venue table
    tables = soup.select("body div.grid.grid--no-gutter table.simple-table")
    
    if tables:
        table_rows = tables[0].select("tr")
        
        if len(table_rows) > 0:
            # Get trading venue name from first row
            first_row_cells = table_rows[0].select("td")
            if first_row_cells:
                venue_name = first_row_cells[0].text.strip()
                
                # Get notation ID from data-plugin attribute in last row
                last_row = table_rows[-1]
                link = last_row.select_one("a")
                
                if link and "data-plugin" in link.attrs:
                    data_plugin = link.attrs["data-plugin"]
                    
                    # Extract ID_NOTATION from data-plugin string
                    if "ID_NOTATION%3D" in data_plugin:
                        notation_id = data_plugin.split("ID_NOTATION%3D")[1].split("%26")[0]
                        id_notations_dict[venue_name] = notation_id
    
    return id_notations_dict


def categorize_lt_ex_venues(venues: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Categorize venues into Life Trading (LT) and Exchange Trading (EX).
    
    Life Trading venues typically start with "LT " prefix.
    Exchange Trading venues are regular stock exchange names.
    
    Args:
        venues: Dictionary mapping venue names to ID_NOTATIONs
        
    Returns:
        Tuple of (lt_venue_dict, ex_venue_dict)
        
    Example:
        Input: {"LT Société Générale": "123", "Xetra": "456"}
        Output: ({"LT Société Générale": "123"}, {"Xetra": "456"})
    """
    lt_venue_dict = {}
    ex_venue_dict = {}
    
    for venue, notation in venues.items():
        if venue.startswith("LT "):
            # Life Trading venue
            lt_venue_dict[venue] = notation
        else:
            # Exchange Trading venue
            ex_venue_dict[venue] = notation
    
    return lt_venue_dict, ex_venue_dict


def extract_preferred_lt_notation(
    soup: BeautifulSoup, 
    lt_venue_dict: Dict[str, str],
    use_single_venue_fallback: bool = False
) -> Optional[str]:
    """
    Extract preferred Life Trading ID_NOTATION based on highest "Gestellte Kurse".
    
    Args:
        soup: BeautifulSoup object containing the instrument page HTML
        lt_venue_dict: Dictionary mapping venue names to ID_NOTATIONs
        use_single_venue_fallback: If True, return single venue as preferred
        
    Returns:
        The ID_NOTATION with highest "Gestellte Kurse", or None if not found
    """
    if not lt_venue_dict:
        return None
    
    # If only one Life Trading venue and fallback enabled, return it as preferred
    if use_single_venue_fallback and len(lt_venue_dict) == 1:
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
                        id_not = extract_id_notation_from_data_plugin(data_plugin)
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
    
    # If no table found and fallback enabled, return first venue as fallback
    if use_single_venue_fallback and lt_venue_dict:
        return list(lt_venue_dict.values())[0]
    
    return None


def extract_preferred_ex_notation(
    soup: BeautifulSoup, 
    ex_venue_dict: Dict[str, str],
    use_single_venue_fallback: bool = False
) -> Optional[str]:
    """
    Extract preferred Exchange Trading ID_NOTATION based on highest "Anzahl Kurse".
    
    Args:
        soup: BeautifulSoup object containing the instrument page HTML
        ex_venue_dict: Dictionary mapping venue names to ID_NOTATIONs
        use_single_venue_fallback: If True, return single venue as preferred
        
    Returns:
        The ID_NOTATION with highest "Anzahl Kurse", or None if not found
    """
    if not ex_venue_dict:
        return None
    
    # If only one Exchange Trading venue and fallback enabled, return it as preferred
    if use_single_venue_fallback and len(ex_venue_dict) == 1:
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
                        id_not = extract_id_notation_from_data_plugin(data_plugin)
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
    
    # If no table found and fallback enabled, return first venue as fallback
    if use_single_venue_fallback and ex_venue_dict:
        return list(ex_venue_dict.values())[0]
    
    return None
