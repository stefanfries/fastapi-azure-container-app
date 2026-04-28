"""
Unit tests for app.parsers.instruments — pure-function utilities.

Covers:
- valid_id_notation — checks presence in lt/ex dicts
- parse_asset_class — extracts AssetClass from a redirected response URL
- parse_default_id_notation — extracts ID_NOTATION query param
- parse_symbol — extracts stock ticker from Aktieninformationen table

parse_instrument_data is an orchestrator that calls fetch_one, factory, scraper,
and enrichment services; it is covered by integration tests, not unit tests.
"""

import re
import textwrap
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup
from fastapi import HTTPException

from app.models.instruments import AssetClass, Instrument, VenueInfo
from app.parsers.instruments import (
    parse_asset_class,
    parse_default_id_notation,
    parse_symbol,
    valid_id_notation,
)


def _make_response(url: str) -> MagicMock:
    """Return a mock httpx.Response with a specific redirected URL."""
    mock = MagicMock()
    mock.url = MagicMock()
    mock.url.__str__ = lambda self: url
    return mock


def _make_instrument_with_notations(lt: dict[str, str], ex: dict[str, str]) -> Instrument:
    return Instrument(
        name="Test",
        wkn="123456",
        asset_class=AssetClass.STOCK,
        id_notations_life_trading={k: VenueInfo(id_notation=v) for k, v in lt.items()},
        id_notations_exchange_trading={k: VenueInfo(id_notation=v) for k, v in ex.items()},
    )


# ---------------------------------------------------------------------------
# valid_id_notation
# ---------------------------------------------------------------------------

class TestValidIdNotation:
    def test_found_in_lt(self):
        instrument = _make_instrument_with_notations({"LT HSBC": "111"}, {})
        assert valid_id_notation(instrument, "111") is True

    def test_found_in_ex(self):
        instrument = _make_instrument_with_notations({}, {"Xetra": "222"})
        assert valid_id_notation(instrument, "222") is True

    def test_not_found(self):
        instrument = _make_instrument_with_notations({"LT HSBC": "111"}, {"Xetra": "222"})
        assert valid_id_notation(instrument, "999") is False

    def test_empty_notations(self):
        instrument = _make_instrument_with_notations({}, {})
        assert valid_id_notation(instrument, "000") is False


# ---------------------------------------------------------------------------
# parse_asset_class
# ---------------------------------------------------------------------------

class TestParseAssetClass:
    @pytest.mark.parametrize("url_segment, expected", [
        ("aktien", AssetClass.STOCK),
        ("etfs", AssetClass.ETF),
        ("fonds", AssetClass.FONDS),
        ("anleihen", AssetClass.BOND),
        ("optionsscheine", AssetClass.WARRANT),
        ("zertifikate", AssetClass.CERTIFICATE),
        ("indizes", AssetClass.INDEX),
        ("rohstoffe", AssetClass.COMMODITY),
        ("waehrungen", AssetClass.CURRENCY),
    ])
    def test_known_segment(self, url_segment, expected):
        url = f"https://www.comdirect.de/inf/{url_segment}/detail/uebersicht.html"
        response = _make_response(url)
        assert parse_asset_class(response) == expected

    def test_unknown_segment_raises_404(self):
        response = _make_response("https://www.comdirect.de/inf/unknown/detail/uebersicht.html")
        with pytest.raises(HTTPException) as exc_info:
            parse_asset_class(response)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# parse_default_id_notation
# ---------------------------------------------------------------------------

class TestParseDefaultIdNotation:
    def test_extracts_id_notation_from_query(self):
        url = "https://www.comdirect.de/inf/aktien/detail/uebersicht.html?ID_NOTATION=12345678"
        assert parse_default_id_notation(_make_response(url)) == "12345678"

    def test_returns_none_when_no_query_param(self):
        url = "https://www.comdirect.de/inf/aktien/detail/uebersicht.html"
        assert parse_default_id_notation(_make_response(url)) is None


# ---------------------------------------------------------------------------
# parse_symbol
# ---------------------------------------------------------------------------

class TestParseSymbol:
    def _stock_page_with_symbol(self, symbol: str = "NVD") -> BeautifulSoup:
        html = f"""
        <html><body>
          <div>
            <p>Aktieninformationen</p>
            <table>
              <tr><th>Symbol</th><td>{symbol}</td></tr>
            </table>
          </div>
        </body></html>
        """
        return BeautifulSoup(textwrap.dedent(html), "html.parser")

    def test_extracts_symbol_for_stock(self):
        soup = self._stock_page_with_symbol("NVD")
        assert parse_symbol(AssetClass.STOCK, soup) == "NVD"

    def test_returns_none_when_no_symbol_row(self):
        soup = BeautifulSoup("<html><body><p>Aktieninformationen</p><table></table></body></html>", "html.parser")
        assert parse_symbol(AssetClass.STOCK, soup) is None

    def test_non_stock_returns_none_when_no_stammdaten(self):
        """Non-STOCK assets check the Stammdaten section; no section → None."""
        soup = self._stock_page_with_symbol("NVD")
        assert parse_symbol(AssetClass.ETF, soup) is None

    def test_non_stock_extracts_symbol_from_stammdaten(self):
        """Non-STOCK assets extract the Symbol from the Stammdaten section."""
        html = """
        <html><body>
          <div>
            <p>Stammdaten</p>
            <table>
              <tr><th>Symbol</th><td>XAU</td></tr>
            </table>
          </div>
        </body></html>
        """
        soup = BeautifulSoup(textwrap.dedent(html), "html.parser")
        assert parse_symbol(AssetClass.COMMODITY, soup) == "XAU"

    def test_non_stock_returns_none_for_placeholder_symbol(self):
        """Non-STOCK assets return None when the Symbol cell is '--'."""
        html = """
        <html><body>
          <div>
            <p>Stammdaten</p>
            <table>
              <tr><th>Symbol</th><td>--</td></tr>
            </table>
          </div>
        </body></html>
        """
        soup = BeautifulSoup(textwrap.dedent(html), "html.parser")
        assert parse_symbol(AssetClass.INDEX, soup) is None
