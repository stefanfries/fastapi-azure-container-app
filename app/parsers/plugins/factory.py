"""
Factory for creating asset class-specific parsers.

This factory implements a plugin pattern, allowing easy addition of new
asset class parsers without modifying existing code.
"""

from app.models.instruments import AssetClass
from app.parsers.plugins.base_parser import InstrumentParser
from app.parsers.plugins.bond_parser import BondParser
from app.parsers.plugins.certificate_parser import CertificateParser
from app.parsers.plugins.etf_parser import ETFParser
from app.parsers.plugins.fonds_parser import FondsParser
from app.parsers.plugins.special_asset_parser import SpecialAssetParser
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
    _parsers: dict[AssetClass, type[InstrumentParser]] = {}

    @classmethod
    def register_parser(cls, asset_class: AssetClass, parser_class: type[InstrumentParser]):
        """
        Register a parser for a specific asset class.

        Args:
            asset_class: The asset class to register
            parser_class: The parser class for this asset class
        """
        cls._parsers[asset_class] = parser_class

    @classmethod
    def get_parser(cls, asset_class: AssetClass) -> InstrumentParser:
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

        # SpecialAssetParser still needs an asset_class constructor argument
        if parser_class is SpecialAssetParser:
            return parser_class(asset_class)
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

ParserFactory.register_parser(AssetClass.STOCK, StockParser)
ParserFactory.register_parser(AssetClass.BOND, BondParser)
ParserFactory.register_parser(AssetClass.ETF, ETFParser)
ParserFactory.register_parser(AssetClass.FONDS, FondsParser)
ParserFactory.register_parser(AssetClass.CERTIFICATE, CertificateParser)
ParserFactory.register_parser(AssetClass.WARRANT, WarrantParser)

# Special (non-tradeable) asset classes — no venues or id_notations
ParserFactory.register_parser(AssetClass.INDEX, SpecialAssetParser)
ParserFactory.register_parser(AssetClass.COMMODITY, SpecialAssetParser)
ParserFactory.register_parser(AssetClass.CURRENCY, SpecialAssetParser)
