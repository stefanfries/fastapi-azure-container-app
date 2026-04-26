"""
Unit tests for app.parsers.standard_asset_parser.StandardAssetParser.

Covers the static helper methods shared across all concrete parsers.
The inherited interface methods (parse_name, parse_wkn, etc.) are exercised
through the concrete-parser test files in tests/unit/parsers/plugins/.
"""

from datetime import date

import pytest

from app.parsers.standard_asset_parser import StandardAssetParser


class TestParseDate:
    def test_dd_mm_yy(self):
        assert StandardAssetParser._parse_date("18.06.26") == date(2026, 6, 18)

    def test_dd_mm_yyyy(self):
        assert StandardAssetParser._parse_date("18.06.2026") == date(2026, 6, 18)

    def test_first_of_january(self):
        assert StandardAssetParser._parse_date("01.01.2025") == date(2025, 1, 1)

    def test_dash_returns_none(self):
        assert StandardAssetParser._parse_date("--") is None

    def test_ka_returns_none(self):
        assert StandardAssetParser._parse_date("k. A.") is None

    def test_none_returns_none(self):
        assert StandardAssetParser._parse_date(None) is None

    def test_empty_string_returns_none(self):
        assert StandardAssetParser._parse_date("") is None

    def test_whitespace_only_returns_none(self):
        assert StandardAssetParser._parse_date("   ") is None

    def test_leading_trailing_whitespace_stripped(self):
        assert StandardAssetParser._parse_date("  18.06.2026  ") == date(2026, 6, 18)


class TestSplitValueCurrency:
    def test_value_and_eur(self):
        value, currency = StandardAssetParser._split_value_currency("100,00 EUR")
        assert value == pytest.approx(100.0)
        assert currency == "EUR"

    def test_value_and_usd(self):
        value, currency = StandardAssetParser._split_value_currency("225,50 USD")
        assert value == pytest.approx(225.5)
        assert currency == "USD"

    def test_thousands_separator(self):
        value, currency = StandardAssetParser._split_value_currency("1.234,56 USD")
        assert value == pytest.approx(1234.56)
        assert currency == "USD"

    def test_no_currency_suffix(self):
        value, currency = StandardAssetParser._split_value_currency("100,00")
        assert value == pytest.approx(100.0)
        assert currency is None

    def test_dash_returns_none_none(self):
        assert StandardAssetParser._split_value_currency("--") == (None, None)

    def test_none_returns_none_none(self):
        assert StandardAssetParser._split_value_currency(None) == (None, None)

    def test_empty_string_returns_none_none(self):
        assert StandardAssetParser._split_value_currency("") == (None, None)


# ---------------------------------------------------------------------------
# parse_name — exercised via a concrete subclass (StockParser)
# ---------------------------------------------------------------------------

class TestParseName:
    def test_raises_value_error_when_no_h1(self):
        from bs4 import BeautifulSoup

        from app.parsers.plugins.stock_parser import StockParser

        soup = BeautifulSoup("<html><body><p>no headline</p></body></html>", "html.parser")
        with pytest.raises(ValueError, match="H1 headline"):
            StockParser().parse_name(soup)


# ---------------------------------------------------------------------------
# parse_id_notations — exercises the dropdown + categorize path
# ---------------------------------------------------------------------------

class TestParseIdNotations:
    def test_with_dropdown_returns_categorized_venues(self):
        from bs4 import BeautifulSoup

        from app.parsers.plugins.stock_parser import StockParser

        html = """
        <html><body>
          <select id="marketSelect">
            <option label="LT HSBC" value="111"></option>
            <option label="Xetra" value="222"></option>
          </select>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        lt, ex, lt_pref, ex_pref = StockParser().parse_id_notations(soup)
        assert lt is not None
        assert ex is not None
        assert "LT HSBC" in lt
        assert "Xetra" in ex

    def test_empty_page_returns_empty_dicts(self):
        from bs4 import BeautifulSoup

        from app.parsers.plugins.stock_parser import StockParser

        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        lt, ex, lt_pref, ex_pref = StockParser().parse_id_notations(soup)
        assert lt == {}
        assert ex == {}
