"""
Unit tests for app.parsers.instruments — pure-function utilities.

Covers:
- valid_id_notation — checks presence in lt/ex dicts
- parse_asset_class — extracts AssetClass from a redirected response URL
- parse_default_id_notation — extracts ID_NOTATION query param
- parse_symbol — extracts stock ticker from Aktieninformationen table
- parse_instrument_data — cache hit/miss paths via mocked repository
"""

import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

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


# ---------------------------------------------------------------------------
# parse_instrument_data — cache hit / cache miss
# ---------------------------------------------------------------------------

def _make_cached_instrument(wkn: str = "716460", isin: str = "US5949181045") -> Instrument:
    return Instrument(
        name="Microsoft Corp.",
        wkn=wkn,
        isin=isin,
        asset_class=AssetClass.STOCK,
    )


class TestParseInstrumentDataCaching:
    """
    Verifies the MongoDB cache lookup in parse_instrument_data without hitting
    the network or the database.  Both the module-level _repo instance and the
    downstream helpers (fetch_one, build_global_identifiers, …) are patched.
    """

    def _scrape_mocks(self, cached: Instrument):
        """Return a dict of context-manager patches for the scraping path."""
        from unittest.mock import patch
        return [
            patch("app.parsers.instruments.fetch_one"),
            patch("app.parsers.instruments.BeautifulSoup"),
            patch("app.parsers.instruments.parse_asset_class", return_value=AssetClass.STOCK),
            patch("app.parsers.instruments.parse_default_id_notation", return_value="12345678"),
            patch("app.parsers.instruments.parse_symbol", return_value=None),
            patch("app.parsers.instruments.build_global_identifiers", new_callable=AsyncMock, return_value=None),
            patch("app.parsers.plugins.factory.ParserFactory.get_parser"),
        ]

    @pytest.mark.asyncio
    async def test_cache_hit_by_wkn_skips_scraping(self):
        """Fresh WKN cache hit → fetch_one is never called."""
        cached = _make_cached_instrument()

        with (
            patch("app.parsers.instruments._repo") as mock_repo,
            patch("app.parsers.instruments.fetch_one") as mock_fetch,
        ):
            mock_repo.find_by_wkn = AsyncMock(return_value=cached)
            mock_repo.is_cache_valid = AsyncMock(return_value=True)

            from app.parsers.instruments import parse_instrument_data

            result = await parse_instrument_data("716460")

        assert result is cached
        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_hit_by_isin_skips_scraping(self):
        """Fresh ISIN cache hit → fetch_one is never called."""
        cached = _make_cached_instrument()

        with (
            patch("app.parsers.instruments._repo") as mock_repo,
            patch("app.parsers.instruments.fetch_one") as mock_fetch,
        ):
            mock_repo.find_by_isin = AsyncMock(return_value=cached)
            mock_repo.is_cache_valid = AsyncMock(return_value=True)

            from app.parsers.instruments import parse_instrument_data

            result = await parse_instrument_data("US5949181045")

        assert result is cached
        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_stale_cache_triggers_rescrape(self):
        """Stale cache entry → scraping is triggered and save is called."""
        cached = _make_cached_instrument()

        with (
            patch("app.parsers.instruments._repo") as mock_repo,
            patch("app.parsers.instruments.fetch_one") as mock_fetch,
            patch("app.parsers.instruments.BeautifulSoup"),
            patch("app.parsers.instruments.parse_asset_class", return_value=AssetClass.STOCK),
            patch("app.parsers.instruments.parse_default_id_notation", return_value="12345678"),
            patch("app.parsers.instruments.parse_symbol", return_value=None),
            patch("app.parsers.instruments.build_global_identifiers", new_callable=AsyncMock, return_value=None),
            patch("app.parsers.plugins.factory.ParserFactory.get_parser") as mock_factory,
        ):
            mock_repo.find_by_wkn = AsyncMock(return_value=cached)
            mock_repo.is_cache_valid = AsyncMock(return_value=False)
            mock_repo.save = AsyncMock()
            mock_fetch.return_value = MagicMock()

            mock_parser = MagicMock()
            mock_parser.parse_name.return_value = cached.name
            mock_parser.parse_wkn.return_value = cached.wkn
            mock_parser.parse_isin.return_value = cached.isin
            mock_parser.parse_id_notations.return_value = ({}, {}, None, None)
            mock_parser.parse_details.return_value = None
            mock_factory.return_value = mock_parser

            from app.parsers.instruments import parse_instrument_data

            result = await parse_instrument_data("716460")

        mock_fetch.assert_called_once()
        mock_repo.save.assert_awaited_once()
        assert result.wkn == "716460"

    @pytest.mark.asyncio
    async def test_cache_miss_calls_save(self):
        """On a cache miss the scraped instrument is persisted via _repo.save."""
        cached = _make_cached_instrument()

        with (
            patch("app.parsers.instruments._repo") as mock_repo,
            patch("app.parsers.instruments.fetch_one") as mock_fetch,
            patch("app.parsers.instruments.BeautifulSoup"),
            patch("app.parsers.instruments.parse_asset_class", return_value=AssetClass.STOCK),
            patch("app.parsers.instruments.parse_default_id_notation", return_value="12345678"),
            patch("app.parsers.instruments.parse_symbol", return_value=None),
            patch("app.parsers.instruments.build_global_identifiers", new_callable=AsyncMock, return_value=None),
            patch("app.parsers.plugins.factory.ParserFactory.get_parser") as mock_factory,
        ):
            mock_repo.find_by_wkn = AsyncMock(return_value=None)
            mock_repo.save = AsyncMock()
            mock_fetch.return_value = MagicMock()

            mock_parser = MagicMock()
            mock_parser.parse_name.return_value = cached.name
            mock_parser.parse_wkn.return_value = cached.wkn
            mock_parser.parse_isin.return_value = cached.isin
            mock_parser.parse_id_notations.return_value = ({}, {}, None, None)
            mock_parser.parse_details.return_value = None
            mock_factory.return_value = mock_parser

            from app.parsers.instruments import parse_instrument_data

            result = await parse_instrument_data("716460")

        mock_repo.save.assert_awaited_once()
        saved_instrument = mock_repo.save.call_args[0][0]
        assert saved_instrument.wkn == "716460"
        assert result.wkn == "716460"
