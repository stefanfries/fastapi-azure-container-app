"""
Unit tests for app.parsers.special_asset_parser.SpecialAssetParser.

Covers asset_class property, parse_isin (always None),
and parse_id_notations (always all-None tuple).
"""

import pytest

from app.models.instruments import AssetClass
from app.parsers.special_asset_parser import SpecialAssetParser


class TestAssetClass:
    @pytest.mark.parametrize("asset_class", [
        AssetClass.INDEX,
        AssetClass.COMMODITY,
        AssetClass.CURRENCY,
    ])
    def test_asset_class_roundtrip(self, asset_class):
        assert SpecialAssetParser(asset_class).asset_class == asset_class


class TestParseIsin:
    @pytest.mark.parametrize("asset_class", [
        AssetClass.INDEX,
        AssetClass.COMMODITY,
        AssetClass.CURRENCY,
    ])
    def test_always_returns_none(self, asset_class):
        """Special assets never have an ISIN on comdirect."""
        parser = SpecialAssetParser(asset_class)
        assert parser.parse_isin(None) is None  # type: ignore[arg-type]


class TestParseIdNotations:
    def test_returns_four_nones(self):
        """Special assets are not tradeable — no venues or id_notations."""
        parser = SpecialAssetParser(AssetClass.INDEX)
        lt, ex, lt_pref, ex_pref = parser.parse_id_notations(None)  # type: ignore[arg-type]
        assert lt is None
        assert ex is None
        assert lt_pref is None
        assert ex_pref is None


# ---------------------------------------------------------------------------
# parse_name — raises ValueError when no H1 found
# ---------------------------------------------------------------------------

class TestParseName:
    def test_raises_when_no_h1(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><p>nothing</p></body></html>", "html.parser")
        with pytest.raises(ValueError, match="H1 headline"):
            SpecialAssetParser(AssetClass.INDEX).parse_name(soup)

    def test_returns_full_name_without_suffix_removal(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><h1>DAX Index</h1></body></html>", "html.parser")
        assert SpecialAssetParser(AssetClass.INDEX).parse_name(soup) == "DAX Index"


# ---------------------------------------------------------------------------
# parse_wkn — raises ValueError when H2 yields nothing
# ---------------------------------------------------------------------------

class TestParseWkn:
    def test_raises_when_no_h2(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><p>no h2</p></body></html>", "html.parser")
        with pytest.raises(ValueError, match="WKN"):
            SpecialAssetParser(AssetClass.INDEX).parse_wkn(soup)

    def test_extracts_wkn_at_position_2(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(
            "<html><body><h2>WKN WKN WKN846900</h2></body></html>", "html.parser"
        )
        assert SpecialAssetParser(AssetClass.INDEX).parse_wkn(soup) == "WKN846900"
