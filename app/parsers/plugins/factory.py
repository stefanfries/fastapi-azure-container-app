"""
Factory for creating asset class-specific parsers.

This factory implements a plugin pattern, allowing easy addition of new
asset class parsers without modifying existing code.
"""

from typing import Dict, Type

from app.models.basedata import AssetClass
from app.parsers.plugins.base_parser import BaseDataParser
from app.parsers.plugins.stock_parser import StockParser
from app.parsers.plugins.warrant_parser import WarrantParser


class ParserFactory:
    """
    Factory for creating asset class-specific parsers.
    
    This uses a plugin pattern where each asset class has its own parser.
    New asset classes can be added by creating a new parser class and
    registering it here.
    """
    
    # Registry of parser classes for each asset class
    _parsers: Dict[AssetClass, Type[BaseDataParser]] = {}
    
    @classmethod
    def register_parser(cls, asset_class: AssetClass, parser_class: Type[BaseDataParser]):
        """
        Register a parser for a specific asset class.
        
        Args:
            asset_class: The asset class to register
            parser_class: The parser class for this asset class
        """
        cls._parsers[asset_class] = parser_class
    
    @classmethod
    def get_parser(cls, asset_class: AssetClass) -> BaseDataParser:
        """
        Get a parser instance for the specified asset class.
        
        Args:
            asset_class: The asset class to get a parser for
            
        Returns:
            An instance of the appropriate parser
            
        Raises:
            ValueError: If no parser is registered for the asset class
        """
        parser_class = cls._parsers.get(asset_class)
        
        if parser_class is None:
            raise ValueError(f"No parser registered for asset class: {asset_class}")
        
        # For StockParser, we need to pass the asset_class
        if parser_class == StockParser:
            return parser_class(asset_class)
        else:
            return parser_class()
    
    @classmethod
    def is_registered(cls, asset_class: AssetClass) -> bool:
        """
        Check if a parser is registered for the given asset class.
        
        Args:
            asset_class: The asset class to check
            
        Returns:
            True if a parser is registered, False otherwise
        """
        return asset_class in cls._parsers


# Register all parsers
# Standard assets use the StockParser
ParserFactory.register_parser(AssetClass.STOCK, StockParser)
ParserFactory.register_parser(AssetClass.BOND, StockParser)
ParserFactory.register_parser(AssetClass.ETF, StockParser)
ParserFactory.register_parser(AssetClass.FONDS, StockParser)
ParserFactory.register_parser(AssetClass.CERTIFICATE, StockParser)

# Warrant uses its own parser
ParserFactory.register_parser(AssetClass.WARRANT, WarrantParser)

# TODO: Add parsers for special asset classes (INDEX, COMMODITY, CURRENCY)
# These would need their own parser implementations
