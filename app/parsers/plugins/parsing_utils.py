"""
Parsing utility functions for common HTML extraction patterns.

This module provides reusable parsing functions that can be shared across
different asset class parsers, promoting DRY principles and consistency.
"""

from typing import Optional

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
