"""
Base parser interface for asset class-specific parsing.

This module defines the abstract base class for all asset class parsers,
implementing a plugin pattern for extensibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

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
    def parse_isin(self, soup: BeautifulSoup) -> Optional[str]:
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
    
    def needs_id_notation_refetch(self) -> bool:
        """
        Indicates whether this asset class needs to be refetched with ID_NOTATION
        to get complete trading venue information.
        
        Some asset classes (like WARRANT) return incomplete data when fetched
        with only WKN, and need to be refetched with an ID_NOTATION parameter.
        
        Returns:
            True if refetch needed, False otherwise
        """
        return False
    
    def parse_default_id_notation_from_url(self, response: httpx.Response) -> Optional[str]:
        """
        Extract the default ID_NOTATION from the response URL.
        
        This is used for asset classes that need to be refetched with ID_NOTATION.
        
        Args:
            response: The HTTP response object
            
        Returns:
            The default ID_NOTATION if found in URL, None otherwise
        """
        import urllib.parse
        
        redirected_url = str(response.url)
        default_id_notation = urllib.parse.parse_qs(
            urllib.parse.urlparse(redirected_url).query
        ).get("ID_NOTATION", [None])[0]
        return default_id_notation
