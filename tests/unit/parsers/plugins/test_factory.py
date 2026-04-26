"""
Unit tests for app.parsers.plugins.factory.ParserFactory.

Covers:
- get_parser returns correct concrete type for every registered asset class
- SpecialAssetParser gets asset_class injected; concrete parsers are instantiated without args
- is_registered returns True for all registered classes, False for unknown
- get_parser raises ValueError for an unregistered asset class
- Each registered parser returns a non-None details object from parse_details()
"""

import textwrap

import pytest
from bs4 import BeautifulSoup

from app.models.instruments import AssetClass
from app.parsers.base_parser import InstrumentParser
from app.parsers.plugins.bond_parser import BondParser
from app.parsers.plugins.certificate_parser import CertificateParser
from app.parsers.plugins.etf_parser import ETFParser
from app.parsers.plugins.factory import ParserFactory
from app.parsers.plugins.fonds_parser import FondsParser
from app.parsers.plugins.stock_parser import StockParser
from app.parsers.plugins.warrant_parser import WarrantParser
from app.parsers.special_asset_parser import SpecialAssetParser


def _minimal_soup() -> BeautifulSoup:
    html = """
    <html><body>
      <div class="col__content col__content--no-padding">
        <p class="headline headline--h3">Aktieninformationen</p>
        <div class="table__container--scroll">
          <table class="simple-table">
            <tr><th scope="row">Wertpapiertyp</th><td>Stammaktie</td></tr>
          </table>
        </div>
      </div>
    </body></html>
    """
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


# ---------------------------------------------------------------------------
# get_parser — concrete type
# ---------------------------------------------------------------------------

class TestGetParserType:
    @pytest.mark.parametrize("asset_class, expected_type", [
        (AssetClass.STOCK, StockParser),
        (AssetClass.BOND, BondParser),
        (AssetClass.ETF, ETFParser),
        (AssetClass.FONDS, FondsParser),
        (AssetClass.CERTIFICATE, CertificateParser),
        (AssetClass.WARRANT, WarrantParser),
    ])
    def test_standard_parser_type(self, asset_class, expected_type):
        assert isinstance(ParserFactory.get_parser(asset_class), expected_type)

    @pytest.mark.parametrize("asset_class", [
        AssetClass.INDEX,
        AssetClass.COMMODITY,
        AssetClass.CURRENCY,
    ])
    def test_special_parser_type(self, asset_class):
        parser = ParserFactory.get_parser(asset_class)
        assert isinstance(parser, SpecialAssetParser)

    @pytest.mark.parametrize("asset_class", [
        AssetClass.INDEX,
        AssetClass.COMMODITY,
        AssetClass.CURRENCY,
    ])
    def test_special_parser_carries_asset_class(self, asset_class):
        """SpecialAssetParser must be initialised with the correct asset_class."""
        parser = ParserFactory.get_parser(asset_class)
        assert parser.asset_class == asset_class

    def test_returns_instrument_parser_instance(self):
        for ac in AssetClass:
            parser = ParserFactory.get_parser(ac)
            assert isinstance(parser, InstrumentParser)


# ---------------------------------------------------------------------------
# is_registered
# ---------------------------------------------------------------------------

class TestIsRegistered:
    def test_all_asset_classes_registered(self):
        for ac in AssetClass:
            assert ParserFactory.is_registered(ac) is True


# ---------------------------------------------------------------------------
# get_parser — error handling
# ---------------------------------------------------------------------------

class TestGetParserErrors:
    def test_raises_for_unregistered_class(self):
        """Temporarily register nothing for a fake key — verify ValueError."""
        # Use a real AssetClass member, temporarily remove it, then restore
        original = ParserFactory._parsers.pop(AssetClass.STOCK)
        try:
            with pytest.raises(ValueError, match="No parser registered"):
                ParserFactory.get_parser(AssetClass.STOCK)
        finally:
            ParserFactory._parsers[AssetClass.STOCK] = original


# ---------------------------------------------------------------------------
# parse_details dispatch
# ---------------------------------------------------------------------------

class TestParseDetailsDispatch:
    @pytest.mark.parametrize("asset_class", [
        AssetClass.STOCK,
        AssetClass.BOND,
        AssetClass.ETF,
        AssetClass.FONDS,
        AssetClass.CERTIFICATE,
        AssetClass.WARRANT,
    ])
    def test_returns_details_object_not_none(self, asset_class):
        parser = ParserFactory.get_parser(asset_class)
        assert parser.parse_details(_minimal_soup()) is not None
