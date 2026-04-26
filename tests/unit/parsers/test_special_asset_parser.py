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
